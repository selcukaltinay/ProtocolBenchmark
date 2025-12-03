package com.lpwan.bench.zenoh;

import com.lpwan.bench.common.Payload;
import io.zenoh.Config;
import io.zenoh.Session;
import io.zenoh.Zenoh;
import io.zenoh.keyexpr.KeyExpr;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class ZenohSubscriber {
    private static List<Payload.ParsedPayload> results = new ArrayList<>();

    public static void run() {
        try {
            System.out.println("Zenoh Subscriber Started");

            // Load default config
            Config config = Config.loadDefault();

            // Open session
            Session session = Zenoh.open(config);

            // Declare key expression
            KeyExpr keyExpr = KeyExpr.tryFrom("lpwan/bench/data");

            // Declare subscriber with callback
            session.declareSubscriber(keyExpr, sample -> {
                try {
                    byte[] data = sample.getPayload().toBytes();
                    Payload.ParsedPayload parsed = Payload.parse(data);
                    if (parsed != null) {
                        synchronized (results) {
                            results.add(parsed);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });

            System.out.println("Listening for messages on: lpwan/bench/data");

            // Wait indefinitely
            synchronized (ZenohSubscriber.class) {
                ZenohSubscriber.class.wait();
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void saveResults() {
        try (FileWriter writer = new FileWriter("zenoh_results.csv")) {
            writer.write("timestamp,sequence,latency\n");
            synchronized (results) {
                for (Payload.ParsedPayload p : results) {
                    writer.write(p.timestamp + "," + p.seq + "," + p.latencyMs + "\n");
                }
            }
            System.out.println("Saved " + results.size() + " Zenoh results");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
