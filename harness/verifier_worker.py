"""Reserved trusted verifier entry point; never treats a lifecycle badge as a gate."""
import argparse
from .policy import PolicyError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.parse_args()
    # 0.2 runs the real deterministic gate directly in the controller during mocks.
    # A live pane launch needs qualified isolation and a signed controller request channel.
    raise PolicyError('live verifier pane launcher is not qualified in Harness 0.2')


if __name__ == '__main__':
    main()
