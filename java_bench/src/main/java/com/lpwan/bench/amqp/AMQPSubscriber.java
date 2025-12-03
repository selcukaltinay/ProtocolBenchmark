package com.lpwan.bench.amqp;

import com.lpwan.bench.common.Payload;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.DeliverCallback;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class AMQPSubscriber {
    private static List<Payload.ParsedPayload> results = new ArrayList<>();

    public static void run(String host, int qos) {
        try {
            ConnectionFactory factory = new ConnectionFactory();
            factory.setHost(host);
            factory.setUsername("test");
            factory.setPassword("test");

            Connection connection = factory.newConnection();
            Channel channel = connection.createChannel();

            channel.queueDeclare("test_queue", false, false, false, null);
            System.out.println("AMQP Subscriber Started");

            DeliverCallback deliverCallback = (consumerTag, delivery) -> {
                Payload.ParsedPayload p = Payload.parse(delivery.getBody());
                if (p != null) {
                    synchronized (results) {
                        results.add(p);
                    }
                }
            };

            channel.basicConsume("test_queue", true, deliverCallback, consumerTag -> {
            });

            // Wait indefinitely
            synchronized (AMQPSubscriber.class) {
                AMQPSubscriber.class.wait();
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            saveResults();
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
