import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import glob

# Klasör oluştur
if not os.path.exists("plots"):
    os.makedirs("plots")

# Veriyi oku
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

# Veri tiplerini düzenle
# Bandwidth '50kbit' gibi string geliyor, sıralama için sayısal değere çevirelim (sadece sıralama için)
def parse_bw(bw):
    if bw == "0": return 9999999
    if "kbit" in bw: return int(bw.replace("kbit", "")) * 1000
    if "mbit" in bw: return int(bw.replace("mbit", "")) * 1000000
    return 0

df['bw_val'] = df['Bandwidth'].apply(parse_bw)
df = df.sort_values('bw_val')

# Protokolleri al
protocols = df['Protocol'].unique()

# Grafik Ayarları
sns.set_theme(style="whitegrid")

def create_heatmap(data, x, y, value, title, filename_prefix, agg_func='mean'):
    plt.figure(figsize=(16, 6))
    
    # Pivot table oluştur
    # Birden fazla değer varsa ortalamasını al
    pivot_tables = {}
    min_val = data[value].min()
    max_val = data[value].max()
    
    # Her protokol için subplot
    num_protos = len(protocols)
    fig, axes = plt.subplots(1, num_protos, figsize=(6 * num_protos, 5), sharey=True)
    
    if num_protos == 1: axes = [axes]
    
    for i, proto in enumerate(protocols):
        proto_data = data[data['Protocol'] == proto]
        if proto_data.empty: continue
        
        pivot = proto_data.pivot_table(index=y, columns=x, values=value, aggfunc=agg_func)
        
        sns.heatmap(pivot, ax=axes[i], cmap="viridis_r" if "Latency" in value else "viridis", 
                    annot=True, fmt=".1f", cbar=True, vmin=min_val, vmax=max_val)
        axes[i].set_title(f"{proto.upper()}")
        axes[i].set_xlabel(x)
        if i == 0: axes[i].set_ylabel(y)
        else: axes[i].set_ylabel("")
            
    plt.suptitle(title, fontsize=16)
    plt.tight_layout()
    plt.savefig(f"plots/{filename_prefix}.png")
    print(f"Saved plots/{filename_prefix}.png")
    plt.close()

print("Grafikler oluşturuluyor...")

# 1. Latency Heatmap (Bandwidth vs Delay)
# Loss=0% ve Rate=1 (düşük yük) durumuna odaklanalım ki saf gecikmeyi görelim
subset = df[(df['Loss'] == "0%") & (df['Rate'] == 1)]
if not subset.empty:
    create_heatmap(subset, x="ConfigDelay_ms", y="Bandwidth", value="LatencyAvg_ms", 
                   title="Ortalama Gecikme (ms) - [Loss=0%, Rate=1 msg/s]", 
                   filename_prefix="heatmap_latency_bw_delay")

# 2. Delivery Ratio Heatmap (Bandwidth vs Loss)
# Rate=10 (orta yük) durumuna bakalım
subset = df[df['Rate'] == 10]
if not subset.empty:
    create_heatmap(subset, x="Loss", y="Bandwidth", value="DeliveryRatio", 
                   title="İletim Başarısı (%) - [Rate=10 msg/s]", 
                   filename_prefix="heatmap_delivery_bw_loss")

# 3. Throughput Heatmap (Size vs Rate)
# Bandwidth=0 (Sınırsız) ve Loss=0% (İdeal ağ) durumunda protokolün kapasitesini görelim
subset = df[(df['Bandwidth'] == "0") & (df['Loss'] == "0%")]
if not subset.empty:
    create_heatmap(subset, x="Rate", y="Size", value="Throughput_bps", 
                   title="Throughput (bps) - [Unlimited Network]", 
                   filename_prefix="heatmap_throughput_size_rate")

# 4. Jitter Heatmap (Bandwidth vs Delay)
subset = df[(df['Loss'] == "0%") & (df['Rate'] == 1)]
if not subset.empty:
    create_heatmap(subset, x="ConfigDelay_ms", y="Bandwidth", value="Jitter_ms", 
                   title="Jitter (ms) - [Loss=0%, Rate=1 msg/s]", 
                   filename_prefix="heatmap_jitter_bw_delay")

print("Tamamlandı.")
