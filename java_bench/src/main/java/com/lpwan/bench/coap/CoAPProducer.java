package com.lpwan.bench.coap;

import com.lpwan.bench.common.Payload;
import org.eclipse.californium.core.CoapClient;
import org.eclipse.californium.core.CoapResponse;
import org.eclipse.californium.core.coap.MediaTypeRegistry;

public class CoAPProducer {
    public static void run(String host, int size, double rate, int duration, boolean confirmable) {
        try {
            String uri = "coap://" + host + ":5683/data";
            CoapClient client = new CoapClient(uri);
            if (confirmable) {
                client.useCONs();
            } else {
                client.useNONs();
            }

            System.out.println("CoAP Producer Started (CON=" + confirmable + ")");

            int count = (int) (rate * duration);
            long intervalNs = (long) ((1.0 / rate) * 1_000_000_000.0);

            for (int i = 0; i < count; i++) {
                long start = System.nanoTime();

                byte[] payload = Payload.generate(i, size);

                // Asynchronous send to avoid blocking
                client.post(new org.eclipse.californium.core.CoapHandler() {
                    @Override
                    public void onLoad(CoapResponse response) {
                        // Success
                    }

                    @Override
                    public void onError() {
                        // Error
                    }
                }, payload, MediaTypeRegistry.APPLICATION_OCTET_STREAM);

                long elapsed = System.nanoTime() - start;
                if (intervalNs > elapsed) {
                    long sleepNs = intervalNs - elapsed;
                    long sleepMs = sleepNs / 1_000_000;
                    int sleepNano = (int) (sleepNs % 1_000_000);
                    Thread.sleep(sleepMs, sleepNano);
                }
            }

            System.out.println("Waiting for pending messages...");
            Thread.sleep(5000);
            System.out.println("BENCHMARK_SENT_COUNT: " + count);
            client.shutdown();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
