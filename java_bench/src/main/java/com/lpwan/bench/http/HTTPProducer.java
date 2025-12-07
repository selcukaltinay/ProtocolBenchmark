package com.lpwan.bench.http;

import com.lpwan.bench.common.Payload;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.ByteArrayEntity;
import org.apache.hc.core5.util.Timeout;

public class HTTPProducer {
    public static void run(String host, int size, double rate, int duration) {
        // Configure timeouts: 10s connection, 30s request
        RequestConfig config = RequestConfig.custom()
                .setConnectTimeout(Timeout.ofSeconds(10))
                .setResponseTimeout(Timeout.ofSeconds(30))
                .build();

        try (CloseableHttpClient client = HttpClients.custom()
                .setDefaultRequestConfig(config)
                .build()) {
            String url = "http://" + host + ":8000/data";
            System.out.println("HTTP Producer Started");

            int count = (int) (rate * duration);
            long intervalNs = (long) ((1.0 / rate) * 1_000_000_000.0);

            for (int i = 0; i < count; i++) {
                long start = System.nanoTime();

                byte[] payload = Payload.generate(i, size);
                HttpPost post = new HttpPost(url);
                post.setEntity(new ByteArrayEntity(payload, ContentType.APPLICATION_OCTET_STREAM));

                client.execute(post, response -> {
                    return null;
                });

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

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
