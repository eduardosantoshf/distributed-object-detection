import argparse

def main(server_address, server_port):
    pass



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", help="server address", default="localhost")
    parser.add_argument("--server-port", help="server address port", default=3456)
    args = parser.parse_args()

    main(args.server_address, args.server_port)
