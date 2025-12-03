package com.lpwan.bench.http;

import com.lpwan.bench.common.Payload;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.List;

public class HTTPSubscriber {
    private static List<Payload.ParsedPayload> results = new ArrayList<>();

    public static void run() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress(8000), 0);
            server.createContext("/data", new DataHandler());
            server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(10)); // Thread pool
            server.start();
            System.out.println("HTTP Subscriber Started on port 8000");

            // Wait indefinitely
            synchronized (HTTPSubscriber.class) {
                HTTPSubscriber.class.wait();
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            saveResults();
        }
    }

    static class DataHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange t) throws IOException {
            if ("POST".equals(t.getRequestMethod())) {
                InputStream is = t.getRequestBody();
                byte[] payload = is.readAllBytes();

                Payload.ParsedPayload p = Payload.parse(payload);
                if (p != null) {
                    synchronized (results) {
                        results.add(p);
                    }
                }

                String response = "OK";
                t.sendResponseHeaders(200, response.length());
                OutputStream os = t.getResponseBody();
                os.write(response.getBytes());
                os.close();
            } else {
                t.sendResponseHeaders(405, -1); // Method Not Allowed
            }
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
