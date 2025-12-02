import pandas as pd
import os

INPUT_FILE = "experiment_results.csv"

if os.path.exists(INPUT_FILE):
    try:
        df = pd.read_csv(INPUT_FILE)
        df = df.dropna(subset=['Protocol'])
        protocols = df['Protocol'].unique()
        
        for proto in protocols:
            # Dosya adında tire yerine alt çizgi kullanalım (örn: coap-con -> coap_con)
            safe_proto = str(proto).replace('-', '_')
            output_file = f"results_{safe_proto}.csv"
            
            proto_df = df[df['Protocol'] == proto]
            proto_df.to_csv(output_file, index=False)
            print(f"Created {output_file} with {len(proto_df)} rows.")
            
    except Exception as e:
        print(f"Error splitting CSV: {e}")
else:
    print(f"{INPUT_FILE} not found.")
