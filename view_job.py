"""View the first circuit's measurement counts from an IBM Sampler job."""

import argparse
from getpass import getpass
from pathlib import Path

import matplotlib.pyplot as plt
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.exceptions import AccountNotFoundError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id", nargs="?", help="IBM Quantum job ID")
    args = parser.parse_args()
    job_id = args.job_id or input("Paste your IBM Quantum job ID: ").strip()
    if not job_id.isalnum():
        parser.error("Enter the alphanumeric job ID from the IBM dashboard.")
    try:
        service = QiskitRuntimeService()
    except AccountNotFoundError:
        print("Copy the API key from your IBM Quantum Platform dashboard.")
        token = getpass("Paste your IBM API key (input hidden): ").strip()
        if not token:
            parser.exit(1, "An API key is required to retrieve this job.\n")
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
    job = service.job(job_id)
    counts = job.result()[0].join_data().get_counts()
    top = sorted(counts, key=counts.get, reverse=True)[:20]
    labels = [hex(int(bits, 2)) for bits in top]
    print(f"{sum(counts.values())} shots, {len(counts)} distinct outcomes")
    for label, bits in zip(labels, top):
        print(f"{label:>12}  {counts[bits]} shots")
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.bar(labels, [counts[bits] for bits in top])
    ax.set(xlabel="Measurement outcome (hex)", ylabel="Shots",
           title=f"Top {len(top)} outcomes for {job_id}")
    ax.tick_params(axis="x", labelrotation=60)
    path = Path.cwd() / f"{job_id}_histogram.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"Histogram saved to {path}")


if __name__ == "__main__":
    main()
