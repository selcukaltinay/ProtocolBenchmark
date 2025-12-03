package com.lpwan.bench.coap;

import com.lpwan.bench.common.Payload;
import org.eclipse.californium.core.CoapResource;
import org.eclipse.californium.core.CoapServer;
import org.eclipse.californium.core.server.resources.CoapExchange;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class CoAPSubscriber {
    private static List<Payload.ParsedPayload> results = new ArrayList<>();

    public static void run() {
        try {
            CoapServer server = new CoapServer();
            server.add(new DataResource("data"));
            server.start();
            System.out.println("CoAP Subscriber Started");

            // Wait indefinitely
            synchronized (CoAPSubscriber.class) {
                CoAPSubscriber.class.wait();
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            saveResults();
        }
    }

    static class DataResource extends CoapResource {
        public DataResource(String name) {
            super(name);
        }

        @Override
        public void handlePOST(CoapExchange exchange) {
            byte[] payload = exchange.getRequestPayload();
            Payload.ParsedPayload p = Payload.parse(payload);
            if (p != null) {
                synchronized (results) {
                    results.add(p);
                }
            }
            exchange.respond("OK");
        }
    }

    public static void saveResults() {
        try (FileWriter writer = new FileWriter("results.csv")) {
            writer.write("timestamp,sequence,latency\n");
            synchronized (results) {
                for (Payload.ParsedPayload p : results) {
                    writer.write(p.timestamp + "," + p.seq + "," + p.latencyMs + "\n");
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
