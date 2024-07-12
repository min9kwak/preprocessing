import argparse


def str2bool(string: str):
    """
    string to boolean
    ex) parser.add_argument('--argument', type=str2bool, default=True)
    """
    if string.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif string.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
