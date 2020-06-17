import argparse

def main(max_persons):
    pass



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", help="maximum number of persons in a frame", default=10)
    args = parser.parse_args()

    main(args.max)
