package com.lpwan.bench.amqp;

import com.lpwan.bench.common.Payload;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.MessageProperties;

public class AMQPProducer {
    public static void run(String host, int size, double rate, int duration, int qos) {
        try {
            ConnectionFactory factory = new ConnectionFactory();
            factory.setHost(host);
            factory.setUsername("test");
            factory.setPassword("test");
            factory.setConnectionTimeout(10000);  // 10 seconds
            factory.setHandshakeTimeout(10000);   // 10 seconds
            factory.setRequestedHeartbeat(30);    // 30 seconds

            try (Connection connection = factory.newConnection();
                    Channel channel = connection.createChannel()) {

                channel.queueDeclare("test_queue", false, false, false, null);

                if (qos == 1) {
                    channel.confirmSelect();
                }

                System.out.println("AMQP Producer Started (QoS " + qos + ")");

                int count = (int) (rate * duration);
                long intervalNs = (long) ((1.0 / rate) * 1_000_000_000.0);

                for (int i = 0; i < count; i++) {
                    long start = System.nanoTime();

                    byte[] payload = Payload.generate(i, size);

                    channel.basicPublish("", "test_queue",
                            (qos == 1) ? MessageProperties.PERSISTENT_TEXT_PLAIN : MessageProperties.MINIMAL_BASIC,
                            payload);

                    if (qos == 1) {
                        // Batch confirm yapılabilir ama basitlik için her mesajda beklemiyoruz
                        // channel.waitForConfirms(); // Bu çok yavaşlatır
                    }

                    long elapsed = System.nanoTime() - start;
                    if (intervalNs > elapsed) {
                        long sleepNs = intervalNs - elapsed;
                        long sleepMs = sleepNs / 1_000_000;
                        int sleepNano = (int) (sleepNs % 1_000_000);
                        Thread.sleep(sleepMs, sleepNano);
                    }
                }

                System.out.println("Waiting for pending messages...");
                if (qos == 1) {
                    try {
                        channel.waitForConfirmsOrDie(5000);
                    } catch (Exception e) {
                    }
                }
                Thread.sleep(5000);
                System.out.println("BENCHMARK_SENT_COUNT: " + count);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
