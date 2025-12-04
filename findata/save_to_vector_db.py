import argparse
from pathlib import Path

from findata.call_findata_api import fetch_findata
from findata.simple_chunk import chunk
from findata.vector_db import save_vector_db

BASE_DIR = Path(__file__).resolve().parent.parent
save_path = BASE_DIR / "findata" / "qdrant_localdb"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This is saving findata to qdrant vector db"
    )
    # ["fixed_deposit", "installment_deposit", "jeonse_loan", "all", "all_apart"] 중 하나
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default="fixed_deposit",
        help="category of finance data",
    )
    parser.add_argument(
        "--save_to",
        "-s",
        type=str,
        default="local",
        help="category of finance data",
    )
    args = parser.parse_args()
    if args.category == "all":
        data = []
        data.extend(fetch_findata(category="fixed_deposit"))
        data.extend(fetch_findata(category="installment_deposit"))
        data.extend(fetch_findata(category="jeonse_loan"))

        save_vector_db(
            chunk(data), category=args.category, path=save_path, save_to=args.save_to
        )

    elif args.category == "all_apart":
        data1 = fetch_findata(category="fixed_deposit")
        save_vector_db(
            chunk(data1), category="fixed_deposit", path=save_path, save_to=args.save_to
        )

        data2 = fetch_findata(category="installment_deposit")
        save_vector_db(
            chunk(data2),
            category="installment_deposit",
            path=save_path,
            save_to=args.save_to,
        )

        data3 = fetch_findata(category="jeonse_loan")
        save_vector_db(
            chunk(data3), category="jeonse_loan", path=save_path, save_to=args.save_to
        )

    else:
        data = fetch_findata(category=args.category)
        save_vector_db(
            chunk(data), category=args.category, path=save_path, save_to=args.save_to
        )
