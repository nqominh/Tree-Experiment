"""
batch_runner.py â€” Batch HO-Tree Builder

Process multiple HTML tables through tree building and save results
in txt or JSON format.

Usage:
    python -m experiment.batch_runner --data-dir RealHiTBench/html --n 5 --output results.txt
    python -m experiment.batch_runner --data-dir RealHiTBench/html --n 10 --output results.json --format json
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiment.tree_builder import html_to_tree
from experiment.tree_output import tree_to_hierarchical_string, tree_to_schema, tree_to_json
from experiment.data_loader import discover_html_tables


def process_tables(tables: dict, max_header_rows: int = 2):
    """Process each table through html_to_tree and collect results."""
    results = []

    for table_id, html in tables.items():
        print(f"Processing {table_id}...")
        result = {
            "table_id": table_id,
            "html_length": len(html),
            "tree_success": False,
            "strategy": "failed",
            "error": None,
        }

        try:
            tree, strategy = html_to_tree(html, max_header_rows=max_header_rows)

            if tree is not None:
                result["tree_success"] = True
                result["strategy"] = strategy
                result["cols"] = tree.get_max_col()
                result["rows"] = tree.get_max_row()
                result["schema"] = tree_to_schema(tree)
                result["hierarchical"] = tree_to_hierarchical_string(tree)
                result["json"] = tree_to_json(tree)
                print(f"  SUCCESS - {strategy} - {result['cols']} cols x {result['rows']} rows")
            else:
                result["error"] = "All strategies failed"
                print("  FAILED")

        except Exception as e:
            result["error"] = str(e)
            print(f"  ERROR: {e}")

        results.append(result)

    return results


def save_results_txt(results: list, output_file: str):
    """Save results in readable text format."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"HO-Tree Batch Results â€” {len(results)} tables\n")
        f.write("=" * 80 + "\n\n")

        for i, r in enumerate(results, 1):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"Table {i}/{len(results)}: {r['table_id']}\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"HTML Length: {r['html_length']} chars\n")
            f.write(f"Success: {r['tree_success']}\n")
            f.write(f"Strategy: {r['strategy']}\n")

            if r["tree_success"]:
                f.write(f"Dimensions: {r['cols']} cols Ã— {r['rows']} rows\n")
                f.write(f"\nSchema:\n")
                for col in r["schema"]:
                    f.write(f"  - {col}\n")
                f.write(f"\nHierarchical Tree:\n")
                f.write(r["hierarchical"] + "\n")
                f.write(f"\nJSON Structure:\n")
                f.write(json.dumps(r["json"], indent=2, ensure_ascii=False)[:2000] + "\n")
            else:
                f.write(f"Error: {r.get('error', 'Unknown')}\n")

            f.write("\n")


def save_results_json(results: list, output_file: str):
    """Save results in JSON format."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Batch HO-Tree builder")
    parser.add_argument("--data-dir", required=True, help="Directory containing HTML files")
    parser.add_argument("--n", type=int, default=5, help="Number of tables to process")
    parser.add_argument("--output", default="tree_batch_results.txt", help="Output file path")
    parser.add_argument("--format", choices=["txt", "json"], default="txt", help="Output format")
    parser.add_argument("--header-rows", type=int, default=2, help="Max header rows for fixed strategy")
    args = parser.parse_args()

    print(f"Discovering HTML tables in {args.data_dir}...")
    tables = discover_html_tables(args.data_dir, limit=args.n)
    print(f"Found {len(tables)} tables\n")

    if not tables:
        print("ERROR: No HTML tables found")
        sys.exit(1)

    print(f"Processing {len(tables)} tables...\n")
    results = process_tables(tables, max_header_rows=args.header_rows)

    if args.format == "json":
        save_results_json(results, args.output)
    else:
        save_results_txt(results, args.output)

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    success_count = sum(1 for r in results if r["tree_success"])
    print(f"Total tables: {len(results)}")
    print(f"Successful: {success_count} ({success_count / len(results) * 100:.1f}%)")
    print(f"Failed: {len(results) - success_count}")
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()

