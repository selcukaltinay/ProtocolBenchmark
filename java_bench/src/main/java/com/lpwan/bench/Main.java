package com.lpwan.bench;

import com.lpwan.bench.mqtt.MQTTProducer;
import com.lpwan.bench.mqtt.MQTTSubscriber;
import com.lpwan.bench.amqp.AMQPProducer;
import com.lpwan.bench.amqp.AMQPSubscriber;
import com.lpwan.bench.coap.CoAPProducer;
import com.lpwan.bench.coap.CoAPSubscriber;
import com.lpwan.bench.http.HTTPProducer;
import com.lpwan.bench.http.HTTPSubscriber;
import com.lpwan.bench.xmpp.XMPPProducer;
import com.lpwan.bench.xmpp.XMPPSubscriber;
import com.lpwan.bench.mqtt.*;
import com.lpwan.bench.amqp.*;
import com.lpwan.bench.coap.*;
import com.lpwan.bench.http.*;
import com.lpwan.bench.xmpp.*;
import com.lpwan.bench.zenoh.ZenohProducer;
import com.lpwan.bench.zenoh.ZenohSubscriber;

public class Main {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: java -jar bench.jar <mode> <protocol> [args...]");
            return;
        }

        String mode = args[0]; // producer or subscriber
        String protocol = args[1];

        // Args parsing
        String host = (args.length > 2) ? args[2] : "localhost";

        if (mode.equals("producer")) {
            int size = (args.length > 3) ? Integer.parseInt(args[3]) : 100;
            double rate = (args.length > 4) ? Double.parseDouble(args[4]) : 1.0;
            int duration = (args.length > 5) ? Integer.parseInt(args[5]) : 10;
            String extra = (args.length > 6) ? args[6] : "";

            if (protocol.startsWith("mqtt")) {
                int qos = 0;
                if (extra.equals("1"))
                    qos = 1;
                if (extra.equals("2"))
                    qos = 2;
                MQTTProducer.run(host, size, rate, duration, qos);
            } else if (protocol.startsWith("amqp")) {
                int qos = 0;
                if (extra.equals("1"))
                    qos = 1;
                AMQPProducer.run(host, size, rate, duration, qos);
            } else if (protocol.startsWith("coap")) {
                boolean confirmable = extra.equals("con");
                CoAPProducer.run(host, size, rate, duration, confirmable);
            } else if (protocol.equals("http")) {
                HTTPProducer.run(host, size, rate, duration);
            } else if (protocol.startsWith("zenoh")) {
                String reliability = "best_effort";
                if (extra.equals("reliable"))
                    reliability = "reliable";
                ZenohProducer.run(host, size, rate, duration, reliability);
            } else if (protocol.equals("xmpp")) {
                XMPPProducer.run(host, size, rate, duration, extra);
            }

        } else if (mode.equals("subscriber")) {
            String extra = (args.length > 3) ? args[3] : "";

            // Shutdown hook for saving results
            final Thread mainThread = Thread.currentThread();
            Runtime.getRuntime().addShutdownHook(new Thread() {
                public void run() {
                    if (protocol.startsWith("mqtt"))
                        MQTTSubscriber.saveResults();
                    else if (protocol.startsWith("amqp"))
                        AMQPSubscriber.saveResults();
                    else if (protocol.startsWith("coap"))
                        CoAPSubscriber.saveResults();
                    else if (protocol.equals("http"))
                        HTTPSubscriber.saveResults();
                    else if (protocol.equals("xmpp"))
                        XMPPSubscriber.saveResults();
                    else if (protocol.startsWith("zenoh"))
                        ZenohSubscriber.saveResults();
                }
            });

            if (protocol.startsWith("mqtt")) {
                int qos = 0;
                if (extra.equals("1"))
                    qos = 1;
                if (extra.equals("2"))
                    qos = 2;
                MQTTSubscriber.run(host, qos);
            } else if (protocol.startsWith("amqp")) {
                int qos = 0;
                if (extra.equals("1"))
                    qos = 1;
                AMQPSubscriber.run(host, qos);
            } else if (protocol.startsWith("coap")) {
                CoAPSubscriber.run();
            } else if (protocol.equals("http")) {
                HTTPSubscriber.run();
            } else if (protocol.equals("xmpp")) {
                XMPPSubscriber.run(host, extra);
            } else if (protocol.startsWith("zenoh")) {
                ZenohSubscriber.run();
            }
        }
    }
}
