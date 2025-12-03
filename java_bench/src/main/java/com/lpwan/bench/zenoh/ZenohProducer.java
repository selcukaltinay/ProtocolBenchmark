package com.lpwan.bench.zenoh;

import com.lpwan.bench.common.Payload;
import io.zenoh.Config;
import io.zenoh.Session;
import io.zenoh.Zenoh;
import io.zenoh.keyexpr.KeyExpr;
import io.zenoh.bytes.ZBytes;

public class ZenohProducer {
    public static void run(String host, int size, double rate, int duration, String reliability) {
        try {
            System.out.println("Zenoh Producer Started");

            // Load default config
            Config config = Config.loadDefault();

            // Open session
            Session session = Zenoh.open(config);

            // Declare key expression
            KeyExpr keyExpr = KeyExpr.tryFrom("lpwan/bench/data");

            long startTime = System.currentTimeMillis();
            long endTime = startTime + (duration * 1000L);
            long count = 0;
            long intervalNs = (long) (1_000_000_000.0 / rate);

            while (System.currentTimeMillis() < endTime) {
                long loopStart = System.nanoTime();

                byte[] payload = Payload.generate(count++, size);
                ZBytes zBytes = ZBytes.from(payload);
                session.put(keyExpr, zBytes);

                long loopEnd = System.nanoTime();
                long elapsed = loopEnd - loopStart;
                long sleepNs = intervalNs - elapsed;

                if (sleepNs > 0) {
                    long sleepMs = sleepNs / 1_000_000;
                    int sleepNanos = (int) (sleepNs % 1_000_000);
                    Thread.sleep(sleepMs, sleepNanos);
                }
            }

            System.out.println("Waiting for pending messages...");
            Thread.sleep(2000);

            session.close();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
