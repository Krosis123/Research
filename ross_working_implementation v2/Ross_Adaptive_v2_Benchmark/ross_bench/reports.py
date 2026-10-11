"""Aggregate CSVs and produce separate, readable benchmark graphs."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def plot_one(df,col,ylabel,title,path,yscale=None):
    plt.figure(figsize=(8.3,5.2))
    for family in df.family.dropna().unique():
        subset=df[df.family==family].groupby('n')[col].median().sort_index()
        plt.plot(subset.index,subset.values,marker='o',label=family)
    plt.title(title);plt.xlabel('Number of genes (n)');plt.ylabel(ylabel)
    if yscale: plt.yscale(yscale)
    plt.xticks(sorted(df.n.unique()));plt.grid(alpha=.25)
    plt.legend(fontsize=8);plt.tight_layout();plt.savefig(path,dpi=150)
    plt.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--output-dir',default='results/plots')
    args=p.parse_args()
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    frames=[]
    for f in args.files:
        df=pd.read_csv(f)
        df['source_file']=Path(f).name
        frames.append(df)
    total=pd.concat(frames,ignore_index=True)
    ok=total[total.status=='ok'].copy()
    if ok.empty: raise RuntimeError('No successful benchmark rows')
    ok.groupby(['source_file','engine','counting_mode','family','n'],dropna=False).agg(
        cases=('n','size'),q=('logical_qubits','median'),
        mean_recall=('attractor_recall','mean'),
        mean_error=('wrong_run_measurement_rate','mean'),
        elapsed_median=('total_runtime_s','median')).reset_index().to_csv(out/'summary.csv',index=False)
    baseline=ok[(ok.engine=='reduced') & (ok.counting_mode=='exact') & (ok.readout_flip_probability==0)]
    if not baseline.empty:
        plot_one(baseline,'logical_qubits','Full evolution-register qubits (n(T+1))',
                 'Rossini qubit width: same genes, different transient depths',out/'qubit_scaling.png','log')
        plot_one(baseline,'total_runtime_s','Reduced mathematical reference time (seconds)',
                 'Reference-model time — NOT Qiskit Aer runtime',out/'reduced_reference_runtime.png','log')
    readout=ok[ok.readout_flip_probability>0]
    if not readout.empty:
        plot_one(readout,'wrong_run_measurement_rate','Wrong/previous attractor shots (fraction)',
                 'Independent readout-flip proxy error',out/'readout_error.png')
    print('Saved',out)

if __name__=='__main__':main()
