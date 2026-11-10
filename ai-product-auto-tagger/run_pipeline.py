
import subprocess
import sys


PYTHON = sys.executable

STEPS = [
    ("Clothing Segmentation, Classification & Color Detection",
     "src/segment_clothing.py"),

    ("Product Description Generation",
     "src/generate_description.py"),
]


def main():
    print("\nStarting AI Product Auto-Tagger Pipeline")
    print("=" * 50)

    for step_name, script_path in STEPS:
        print(f"\nRunning: {step_name}")
        print("-" * 50)

        result = subprocess.run(
            [PYTHON, script_path],
            check=False
        )

        if result.returncode != 0:
            print(f"\nPipeline stopped: {step_name} failed.")
            sys.exit(result.returncode)

    print("\n" + "=" * 50)
    print("Pipeline completed successfully!")
    print("Check results/products.json for final output.")


if __name__ == "__main__":
    main()

