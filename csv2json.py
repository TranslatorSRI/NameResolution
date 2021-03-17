#!/usr/bin/env python
"""Convert CSV to JSON for upload to Solr."""
import argparse
import csv
import json


def reformat(infile: str, outfile: str, separator: str = ","):
    """Reformat name file."""
    output = []
    with open(infile, "r") as f:
        reader = csv.reader(f, delimiter=separator, quotechar="\"")
        for idx, row in enumerate(reader):
            entity_id = ":".join(row[0].split("/")[-1].split("_"))
            name = row[-1]
            output.append({
                "id": idx,
                "curie": entity_id,
                "name": name,
                "length": len(name)
            })
    with open(outfile, "w") as f:
        json.dump(output, f)


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

    args = parser.parse_args()
    reformat(args.input, args.output, )
