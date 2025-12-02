import pandas as pd

import glob

# Load results
all_files = glob.glob("results_*.csv")
df_list = []
for filename in all_files:
    try:
        df = pd.read_csv(filename)
        df_list.append(df)
    except: pass

if df_list:
    df = pd.concat(df_list, ignore_index=True)
else:
    print("No results found.")
    exit()

# Group by Protocol
print("=== Genel Performans (Ortalama) ===")
summary = df.groupby('Protocol')[['DeliveryRatio', 'LatencyAvg_ms', 'Throughput_bps']].mean()
print(summary)
print("\n")

# Impact of Packet Loss on Delivery Ratio
print("=== Paket Kaybının Teslimat Oranına Etkisi (Delivery Ratio %) ===")
loss_impact = df.pivot_table(index='Protocol', columns='Loss', values='DeliveryRatio', aggfunc='mean')
print(loss_impact)
print("\n")

# Impact of Network Delay on Latency
print("=== Ağ Gecikmesinin Latency'ye Etkisi (ms) ===")
delay_impact = df.pivot_table(index='Protocol', columns='ConfigDelay_ms', values='LatencyAvg_ms', aggfunc='mean')
print(delay_impact)
print("\n")

# Best Protocol for High Loss (10%)
print("=== %10 Paket Kaybında En İyi Protokol ===")
high_loss = df[df['Loss'] == '10%'].groupby('Protocol')['DeliveryRatio'].mean().sort_values(ascending=False)
print(high_loss)
