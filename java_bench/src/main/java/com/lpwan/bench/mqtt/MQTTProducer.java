package com.lpwan.bench.mqtt;

import com.lpwan.bench.common.Payload;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public class MQTTProducer {
    public static void run(String host, int size, double rate, int duration, int qos) {
        try {
            String broker = "tcp://" + host + ":1883";
            String clientId = "JavaMQTTProducer";
            MemoryPersistence persistence = new MemoryPersistence();

            MqttAsyncClient client = new MqttAsyncClient(broker, clientId, persistence);
            MqttConnectOptions connOpts = new MqttConnectOptions();
            connOpts.setCleanSession(false);
            connOpts.setAutomaticReconnect(true);
            connOpts.setConnectionTimeout(10);  // 10 seconds
            connOpts.setKeepAliveInterval(30);  // 30 seconds

            System.out.println("Connecting to broker: " + broker);
            client.connect(connOpts).waitForCompletion(15000);  // 15 second timeout
            System.out.println("Connected");

            int count = (int) (rate * duration);
            long intervalNs = (long) ((1.0 / rate) * 1_000_000_000.0);

            for (int i = 0; i < count; i++) {
                long start = System.nanoTime();

                byte[] payload = Payload.generate(i, size);
                MqttMessage message = new MqttMessage(payload);
                message.setQos(qos);

                // For QoS 1/2, wait for acknowledgment to avoid queue overflow
                if (qos > 0) {
                    client.publish("test/topic", message).waitForCompletion(30000);  // 30s timeout
                } else {
                    client.publish("test/topic", message);
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
            Thread.sleep(5000);

            System.out.println("BENCHMARK_SENT_COUNT: " + count);

            client.disconnect();
            System.out.println("Disconnected");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
