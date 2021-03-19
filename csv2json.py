#!/usr/bin/env python
"""Convert CSV to JSON for upload to Solr."""
import argparse
import csv
import json

from tqdm import tqdm


def reformat(
        infile: str,
        outfile: str,
        separator: str = ",",
        quotechar: str = "🤪",
):
    """Reformat name file."""
    with open(infile, "r") as f:
        reader = csv.reader(f, delimiter=separator, quotechar=quotechar)
        with open(outfile, "w") as f:
            f.write("[\n")
            for idx, row in tqdm(enumerate(reader)):
                entity_id = ":".join(row[0].split("/")[-1].split("_"))
                name = row[-1]
                if idx:
                    f.write(",\n")
                f.write("\t")
                json.dump({
                    "curie": entity_id,
                    "name": name,
                    "length": len(name)
                }, f)
            f.write("\n]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="reformat a name file"
    )
    parser.add_argument(
        "input",
        type=str,
        help="the input file path",
    )
    parser.add_argument(
        "output",
        type=str,
        help="the output file path",
    )
    parser.add_argument(
        "--sep",
        type=str,
        help="the input file field separator",
        default=",",
    )
    parser.add_argument(
        "--quote",
        type=str,
        help="the input file quote character",
        default="🤪",
    )

    args = parser.parse_args()
    args.sep = args.sep.replace("\\t", "\t")
    reformat(args.input, args.output, args.sep, args.quote)
