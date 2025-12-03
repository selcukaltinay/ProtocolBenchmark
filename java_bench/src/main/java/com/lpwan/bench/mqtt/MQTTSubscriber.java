package com.lpwan.bench.mqtt;

import com.lpwan.bench.common.Payload;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class MQTTSubscriber {
    private static List<Payload.ParsedPayload> results = new ArrayList<>();

    public static void run(String host, int qos) {
        try {
            String broker = "tcp://" + host + ":1883";
            String clientId = "JavaMQTTSubscriber";
            MemoryPersistence persistence = new MemoryPersistence();

            MqttClient client = new MqttClient(broker, clientId, persistence);
            MqttConnectOptions connOpts = new MqttConnectOptions();
            connOpts.setCleanSession(false);
            connOpts.setAutomaticReconnect(true);

            client.setCallback(new MqttCallback() {
                public void connectionLost(Throwable cause) {
                    System.out.println("Connection lost");
                }

                public void messageArrived(String topic, MqttMessage message) throws Exception {
                    Payload.ParsedPayload p = Payload.parse(message.getPayload());
                    if (p != null) {
                        synchronized (results) {
                            results.add(p);
                        }
                    }
                }

                public void deliveryComplete(IMqttDeliveryToken token) {
                }
            });

            System.out.println("Connecting to broker: " + broker);
            client.connect(connOpts);
            client.subscribe("test/topic", qos);
            System.out.println("Subscribed");

            // Wait for termination signal (Main loop handles this via Thread.join or
            // similar)
            // For now, we just wait indefinitely until killed or interrupted
            synchronized (MQTTSubscriber.class) {
                MQTTSubscriber.class.wait();
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
