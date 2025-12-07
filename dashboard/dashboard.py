from flask import Flask, render_template, jsonify, request
import os
import json
import pandas as pd
import subprocess
import glob
from datetime import datetime

app = Flask(__name__)

# Deney parametreleri (run_experiments.py ile aynı)
PROTOCOLS = [
    "mqtt-qos0", "mqtt-qos1", "mqtt-qos2",
    "amqp-qos0", "amqp-qos1",
    "coap-con", "coap-non", "http",
    "xmpp-qos0", "xmpp-qos1", "xmpp-qos2",
    "zenoh-best-effort", "zenoh-reliable"
]
PAYLOAD_SIZES = [16, 128]
RATES = [1, 10, 100]
BANDWIDTHS = ["50kbit", "100kbit", "250kbit", "1mbit"]
LOSSES = ["0%", "1%", "5%", "10%"]
DELAYS = [0, 20, 100, 500]
RESULTS_DIR = "../results"

def calculate_total_tests():
    """Toplam test sayısını hesapla"""
    return len(PROTOCOLS) * len(PAYLOAD_SIZES) * len(RATES) * len(BANDWIDTHS) * len(LOSSES) * len(DELAYS)

def get_experiment_status():
    """Her protokol için ilerleme durumunu hesapla"""
    total_per_protocol = len(PAYLOAD_SIZES) * len(RATES) * len(BANDWIDTHS) * len(LOSSES) * len(DELAYS)
    
    status = {}
    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")
        
        completed = 0
        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)
                completed = len(df)
            except:
                completed = 0
        
        status[proto] = {
            'completed': completed,
            'total': total_per_protocol,
            'percentage': round((completed / total_per_protocol) * 100, 1) if total_per_protocol > 0 else 0
        }
    
    # Genel ilerleme
    total_completed = sum(s['completed'] for s in status.values())
    total_tests = calculate_total_tests()
    
    return {
        'protocols': status,
        'overall': {
            'completed': total_completed,
            'total': total_tests,
            'percentage': round((total_completed / total_tests) * 100, 1) if total_tests > 0 else 0
        }
    }

def get_experiment_process_status():
    """run_experiments.py processinin çalışıp çalışmadığını kontrol et"""
    try:
        result = subprocess.run(['pgrep', '-f', 'run_experiments.py'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_latest_results():
    """En son sonuçları al"""
    results = {}
    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")
        
        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)
                if len(df) > 0:
                    # Son 10 test sonucu
                    recent = df.tail(10).to_dict('records')
                    
                    # Özet istatistikler
                    summary = {
                        'avg_delivery': round(df['DeliveryRatio'].mean(), 2),
                        'avg_latency': round(df['LatencyAvg_ms'].mean(), 2),
                        'avg_throughput': round(df['Throughput_bps'].mean(), 2),
                        'total_tests': len(df)
                    }
                    
                    results[proto] = {
                        'recent': recent,
                        'summary': summary
                    }
            except Exception as e:
                results[proto] = {'error': str(e)}
    
    return results

def get_comparison_data(filters=None):
    """Protokoller arası karşılaştırma verisi"""
    comparison = []

    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")

        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)

                # Filtreleri uygula
                if filters and len(df) > 0:
                    if filters.get('size'):
                        df = df[df['Size'] == int(filters['size'])]
                    if filters.get('bandwidth'):
                        df = df[df['Bandwidth'] == filters['bandwidth']]
                    if filters.get('loss'):
                        df = df[df['Loss'] == filters['loss']]
                    if filters.get('delay'):
                        df = df[df['ConfigDelay_ms'] == int(filters['delay'])]

                if len(df) > 0:
                    comparison.append({
                        'protocol': proto,
                        'avg_delivery': round(df['DeliveryRatio'].mean(), 2),
                        'avg_latency': round(df['LatencyAvg_ms'].mean(), 2),
                        'avg_throughput': round(df['Throughput_bps'].mean(), 2),
                        'total_tests': len(df)
                    })
            except:
                pass

    return comparison

def get_detailed_stats():
    """Detaylı istatistikler - Her protokol için min/max/median/percentile"""
    stats = {}

    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")

        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)
                if len(df) > 0:
                    stats[proto] = {
                        'delivery': {
                            'mean': round(df['DeliveryRatio'].mean(), 2),
                            'min': round(df['DeliveryRatio'].min(), 2),
                            'max': round(df['DeliveryRatio'].max(), 2),
                            'median': round(df['DeliveryRatio'].median(), 2),
                            'p95': round(df['DeliveryRatio'].quantile(0.95), 2),
                            'std': round(df['DeliveryRatio'].std(), 2)
                        },
                        'latency': {
                            'mean': round(df['LatencyAvg_ms'].mean(), 2),
                            'min': round(df['LatencyAvg_ms'].min(), 2),
                            'max': round(df['LatencyAvg_ms'].max(), 2),
                            'median': round(df['LatencyAvg_ms'].median(), 2),
                            'p95': round(df['LatencyAvg_ms'].quantile(0.95), 2),
                            'std': round(df['LatencyAvg_ms'].std(), 2)
                        },
                        'jitter': {
                            'mean': round(df['Jitter_ms'].mean(), 2) if 'Jitter_ms' in df.columns else 0,
                            'min': round(df['Jitter_ms'].min(), 2) if 'Jitter_ms' in df.columns else 0,
                            'max': round(df['Jitter_ms'].max(), 2) if 'Jitter_ms' in df.columns else 0,
                            'median': round(df['Jitter_ms'].median(), 2) if 'Jitter_ms' in df.columns else 0
                        },
                        'throughput': {
                            'mean': round(df['Throughput_bps'].mean(), 2),
                            'min': round(df['Throughput_bps'].min(), 2),
                            'max': round(df['Throughput_bps'].max(), 2),
                            'median': round(df['Throughput_bps'].median(), 2)
                        }
                    }
            except Exception as e:
                stats[proto] = {'error': str(e)}

    return stats

def get_filtered_data(filters=None):
    """Filtrelenmiş veri - bandwidth, loss, delay, protocol gibi filtrelere göre"""
    all_data = []

    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")

        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)
                if len(df) > 0:
                    # Kolon adlarını standartlaştır
                    if 'ConfigDelay_ms' in df.columns:
                        df['Delay_ms'] = df['ConfigDelay_ms']
                    if 'Size' in df.columns:
                        df['PayloadSize_bytes'] = df['Size']
                    if 'Rate' in df.columns:
                        df['Rate_msg_s'] = df['Rate']

                    # Filtre uygula
                    if filters:
                        if 'protocol' in filters and filters['protocol']:
                            if proto != filters['protocol']:
                                continue
                        if 'bandwidth' in filters and filters['bandwidth']:
                            df = df[df['Bandwidth'] == filters['bandwidth']]
                        if 'loss' in filters and filters['loss']:
                            df = df[df['Loss'] == filters['loss']]
                        if 'delay' in filters and filters['delay']:
                            df = df[df['Delay_ms'] == int(filters['delay'])]
                        if 'payload_size' in filters and filters['payload_size']:
                            df = df[df['PayloadSize_bytes'] == int(filters['payload_size'])]

                    # DataFrame'i dict'e çevir
                    for _, row in df.iterrows():
                        all_data.append(row.to_dict())
            except:
                pass

    return all_data

def get_network_condition_comparison():
    """Ağ koşullarına göre karşılaştırma"""
    results = {
        'by_bandwidth': {},
        'by_loss': {},
        'by_delay': {}
    }

    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")

        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)
                if len(df) > 0:
                    # Bandwidth bazlı
                    for bw in BANDWIDTHS:
                        if bw not in results['by_bandwidth']:
                            results['by_bandwidth'][bw] = {}
                        bw_data = df[df['Bandwidth'] == bw]
                        if len(bw_data) > 0:
                            results['by_bandwidth'][bw][proto] = {
                                'delivery': round(bw_data['DeliveryRatio'].mean(), 2),
                                'latency': round(bw_data['LatencyAvg_ms'].mean(), 2),
                                'throughput': round(bw_data['Throughput_bps'].mean(), 2)
                            }

                    # Loss bazlı
                    for loss in LOSSES:
                        if loss not in results['by_loss']:
                            results['by_loss'][loss] = {}
                        loss_data = df[df['Loss'] == loss]
                        if len(loss_data) > 0:
                            results['by_loss'][loss][proto] = {
                                'delivery': round(loss_data['DeliveryRatio'].mean(), 2),
                                'latency': round(loss_data['LatencyAvg_ms'].mean(), 2),
                                'throughput': round(loss_data['Throughput_bps'].mean(), 2)
                            }

                    # Delay bazlı
                    for delay in DELAYS:
                        delay_key = f"{delay}ms"
                        if delay_key not in results['by_delay']:
                            results['by_delay'][delay_key] = {}
                        delay_data = df[df['Delay_ms'] == delay]
                        if len(delay_data) > 0:
                            results['by_delay'][delay_key][proto] = {
                                'delivery': round(delay_data['DeliveryRatio'].mean(), 2),
                                'latency': round(delay_data['LatencyAvg_ms'].mean(), 2),
                                'throughput': round(delay_data['Throughput_bps'].mean(), 2)
                            }
            except:
                pass

    return results

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """İlerleme durumu API"""
    status = get_experiment_status()
    status['running'] = get_experiment_process_status()
    status['timestamp'] = datetime.now().isoformat()
    return jsonify(status)

@app.route('/api/results')
def api_results():
    """Sonuçlar API"""
    results = get_latest_results()
    return jsonify(results)

@app.route('/api/comparison')
def api_comparison():
    """Karşılaştırma API"""
    # Filtreleri al
    filters = {
        'size': request.args.get('size'),
        'bandwidth': request.args.get('bandwidth'),
        'loss': request.args.get('loss'),
        'delay': request.args.get('delay')
    }
    # None değerleri temizle
    filters = {k: v for k, v in filters.items() if v}

    comparison = get_comparison_data(filters if filters else None)
    return jsonify(comparison)

@app.route('/api/control/start', methods=['POST'])
def api_start():
    """Testleri başlat"""
    try:
        # Önce çalışan varsa durdur
        subprocess.run(['pkill', '-f', 'run_experiments.py'], 
                      capture_output=True)
        
        # Yeni testi başlat
        subprocess.Popen(['bash', '-c', 
                         'source venv/bin/activate && nohup python run_experiments.py > experiment_log.txt 2>&1 &'],
                        cwd=os.getcwd())
        
        return jsonify({'success': True, 'message': 'Testler başlatıldı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/control/stop', methods=['POST'])
def api_stop():
    """Testleri durdur"""
    try:
        subprocess.run(['pkill', '-f', 'run_experiments.py'], 
                      capture_output=True)
        return jsonify({'success': True, 'message': 'Testler durduruldu'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """Son logları getir"""
    log_files = [
        '/tmp/final_experiment_run.log',
        '/tmp/experiment_run.log',
        '../experiment_log.txt',
        'experiment_log.txt'
    ]

    for log_file in log_files:
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Son 100 satır
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                    return jsonify({
                        'logs': ''.join(recent_lines),
                        'source': log_file
                    })
        except:
            continue

    return jsonify({'logs': 'Log dosyası bulunamadı', 'source': 'none'})

@app.route('/api/detailed-stats')
def api_detailed_stats():
    """Detaylı istatistikler API"""
    stats = get_detailed_stats()
    return jsonify(stats)

@app.route('/api/filtered-data')
def api_filtered_data():
    """Filtrelenmiş veri API"""
    filters = {
        'protocol': request.args.get('protocol'),
        'bandwidth': request.args.get('bandwidth'),
        'loss': request.args.get('loss'),
        'delay': request.args.get('delay'),
        'payload_size': request.args.get('payload_size')
    }
    data = get_filtered_data(filters)
    return jsonify(data)

@app.route('/api/network-conditions')
def api_network_conditions():
    """Ağ koşulları karşılaştırma API"""
    data = get_network_condition_comparison()
    return jsonify(data)

@app.route('/api/analysis')
def api_analysis():
    """Performans analizi API (Latency/Throughput vs Load)"""
    delay_filter = request.args.get('delay')
    loss_filter = request.args.get('loss')
    
    print(f"[DEBUG] Analysis filters - delay: {delay_filter}, loss: {loss_filter}")
    
    data = {}
    for proto in PROTOCOLS:
        safe_proto = proto.replace('-', '_')
        proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")
        if os.path.exists(proto_file):
            try:
                df = pd.read_csv(proto_file)
                original_len = len(df)
                
                if len(df) > 0:
                    # Filtreleme - CSV'deki sütun isimleri: 'Delay' ve 'Loss'
                    if delay_filter and delay_filter != 'all':
                        try:
                            # Delay sütunu string olabilir ("0ms", "20ms" gibi) veya sayı
                            delay_val = int(delay_filter)
                            # Önce sayısal karşılaştırma dene
                            if 'Delay' in df.columns:
                                # Delay değeri string ise ("20ms") parse et
                                if df['Delay'].dtype == 'object':
                                    df['Delay_numeric'] = df['Delay'].str.replace('ms', '').astype(int)
                                    df = df[df['Delay_numeric'] == delay_val]
                                else:
                                    df = df[df['Delay'] == delay_val]
                            print(f"[DEBUG] {proto}: After delay filter ({delay_filter}ms) - {len(df)} rows (was {original_len})")
                        except Exception as e:
                            print(f"[DEBUG] {proto}: Delay filter error - {e}")
                        
                    if loss_filter and loss_filter != 'all':
                        try:
                            # Loss sütunu string olabilir ("1%") veya sayı
                            loss_val = int(loss_filter.replace('%', ''))
                            before_loss = len(df)
                            
                            if 'Loss' in df.columns:
                                # Loss değeri string ise ("1%") parse et
                                if df['Loss'].dtype == 'object':
                                    df['Loss_numeric'] = df['Loss'].str.replace('%', '').astype(int)
                                    df = df[df['Loss_numeric'] == loss_val]
                                else:
                                    df = df[df['Loss'] == loss_val]
                            print(f"[DEBUG] {proto}: After loss filter ({loss_val}%) - {len(df)} rows (was {before_loss})")
                        except Exception as e:
                            print(f"[DEBUG] {proto}: Loss filter error - {e}")
                    
                    if len(df) > 0:
                        # Rate'e göre grupla ve ortalama al
                        grouped = df.groupby('Rate').agg({
                            'LatencyAvg_ms': 'mean',
                            'Throughput_bps': 'mean'
                        }).reset_index().sort_values('Rate')
                        
                        data[proto] = {
                            'rates': grouped['Rate'].tolist(),
                            'latency': grouped['LatencyAvg_ms'].tolist(),
                            'throughput': grouped['Throughput_bps'].tolist()
                        }
                        print(f"[DEBUG] {proto}: Added to results with {len(grouped)} rate points")
            except Exception as e:
                print(f"[DEBUG] {proto}: Error processing file - {e}")
    
    print(f"[DEBUG] Returning data for {len(data)} protocols")
    return jsonify(data)

@app.route('/api/export/<format>')
def api_export(format):
    """Veri export API - CSV veya JSON"""
    try:
        all_data = []
        for proto in PROTOCOLS:
            safe_proto = proto.replace('-', '_')
            proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")
            if os.path.exists(proto_file):
                df = pd.read_csv(proto_file)
                all_data.append(df)

        if not all_data:
            return jsonify({'error': 'No data available'}), 404

        combined_df = pd.concat(all_data, ignore_index=True)

        if format == 'csv':
            return combined_df.to_csv(index=False), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename=lpwan_results.csv'
            }
        elif format == 'json':
            return combined_df.to_json(orient='records'), 200, {
                'Content-Type': 'application/json',
                'Content-Disposition': 'attachment; filename=lpwan_results.json'
            }
        else:
            return jsonify({'error': 'Invalid format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Results dizinini oluştur
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    print("=" * 60)
    print("🚀 LPWAN Test Dashboard Başlatılıyor...")
    print("=" * 60)
    print(f"📊 Toplam Test Sayısı: {calculate_total_tests()}")
    print(f"🔬 Protokol Sayısı: {len(PROTOCOLS)}")
    print(f"📁 Sonuçlar Dizini: {RESULTS_DIR}/")
    print("=" * 60)
    print("🌐 Dashboard: http://localhost:5001")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
