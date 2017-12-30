"""
    Ledgerlink smart contract
    =========================

    The ledgerlink (A.K.A. ledgr.link) smart contract provides a way to generate shortened-URLs and
    store the related unique codes (as of the the corresponding URL) into the NEO blockchain. This
    has the advantage of allowing to store irreplaceable short URLs in the blockchain. The codes and
    the corresponding URLs cannot be changed by anybody and will live forever on the NEO blockchain.

"""

from boa.blockchain.vm.Neo.Action import RegisterAction
from boa.blockchain.vm.Neo.Blockchain import GetHeight
from boa.blockchain.vm.Neo.Output import GetScriptHash
from boa.blockchain.vm.Neo.Runtime import CheckWitness, GetTrigger, Notify
from boa.blockchain.vm.Neo.Storage import Get, GetContext, Put
from boa.blockchain.vm.Neo.TriggerType import Application, Verification
from boa.blockchain.vm.System.ExecutionEngine import GetScriptContainer
from boa.code.builtins import concat, substr


# -------------------------------------------
# TOKEN SETTINGS
# -------------------------------------------

# Script hash of the contract owner.
OWNER = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

# The URL of the associated URL shortener service.
SHORTENER_URL = 'https://ledgr.link'


# -------------------------------------------
# EVENTS
# -------------------------------------------

DispatchNewURLEvent = RegisterAction('urladd', 'code', 'url')


# -------------------------------------------
# CONTRACT METHODS
# -------------------------------------------

def Main(operation, args):
    """ Main entrypoint for the smart contract.

    :param operation: the operation to be performed
    :param args: a list of arguments (which may be empty, but not absent)
    :type operation: str
    :type args: list
    :return: a boolean, a string or a byte array indicating the result of the execution of the SC
    :rtype: bool, string or bytearray

    """

    arg_length_error = 'Incorrect number of arguments'

    # Uses the trigger to dertermine whether this smart contract is being run in 'verification' mode
    # or 'application' mode.
    trigger = GetTrigger()

    # The 'Verification' mode is used when trying to spend assets (eg. NEO, Gas) on behalf of this
    # contract's address.
    if trigger == Verification():
        # Checks whether the script that sent this is the owner. If so we can allow the operation.
        is_owner = CheckWitness(OWNER)
        if is_owner:
            return True
        return False
    elif trigger == Application():
        if operation == 'shortenerURL':
            url = SHORTENER_URL
            return url
        elif operation == 'addURL':
            if len(args) == 1:
                url = args[0]
                result = add_url(url)
                return result
            return arg_length_error
        elif operation == 'getURL':
            if len(args) == 1:
                code = args[0]
                result = get_url(code)
                return result
            return arg_length_error
        elif operation == 'getURLInfo':
            if len(args) == 1:
                code = args[0]
                result = get_url_info(code)
                return result
            return arg_length_error

        result = 'unknown operation'
        return result

    return False


def add_url(url):
    """ Generates a new code and stores the <code, url> pair into the blockchain. """
    # Retrieves the current "height" of the blockchain, as of the related block and timestamp.
    current_height = GetHeight()

    # Retrieves the hash of the considered sender.
    tx = GetScriptContainer()
    references = tx.References
    ref = references[0]
    sender = GetScriptHash(ref)

    # Generates a unique code.
    s1 = b58encode(current_height, 11)
    s2 = b58encode(sender, 2)
    s3 = b58encode(url, 2)
    code_part1 = concat(s1, s2)
    code = concat(code_part1, s3)
    Notify(code)

    # Puts the URL and the related information into the ledger.
    context = GetContext()
    contextkey_for_url = get_contextkey_for_url(code)
    contextkey_for_sender = get_contextkey_for_sender(code)
    # NOTE: dictionaries are not yey supported by the neo-boa compiler so we have to derive multiple
    # context keys from the code value for each item associated with the considered code.
    Put(context, contextkey_for_url, url)
    Put(context, contextkey_for_sender, sender)

    # Fires an event indicating which <code, url> pair has been persisted into the ledger.
    DispatchNewURLEvent(code, url)

    return True


def get_url(code):
    """ Returns the URL associated with the considered code. """
    context = GetContext()
    contextkey_for_url = get_contextkey_for_url(code)
    url = Get(context, contextkey_for_url)
    return url


def get_url_info(code):
    """ Returns all the information available for the considered code. """
    context = GetContext()
    contextkey_for_url = get_contextkey_for_url(code)
    contextkey_for_sender = get_contextkey_for_sender(code)
    url = Get(context, contextkey_for_url)
    sender = Get(context, contextkey_for_sender)
    result = [url, sender]
    return result


# -------------------------------------------
# UTILITIES
# -------------------------------------------


def b58encode(i, max_length):
    """ Encodes an integer using Base58. """
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    code = '\x00'

    current_length = 0
    while i and (current_length < max_length):
        newi = i // 58
        idx = i % 58
        i = newi
        c = substr(alphabet, idx, 1)

        if code == '\x00':
            code = c
        else:
            code = concat(c, code)

        current_length += 1

    return code


def get_contextkey_for_url(code):
    """ Returns the context key to use for retrieving an URL associated with a code. """
    contextkey = concat(code, '__url')
    return contextkey


def get_contextkey_for_sender(code):
    """ Returns the context key to use for retrieving a sender address associated with a code. """
    contextkey = concat(code, '__sender')
    return contextkey
