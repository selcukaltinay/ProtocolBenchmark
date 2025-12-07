package com.lpwan.bench.xmpp;

import com.lpwan.bench.common.Payload;
import org.jivesoftware.smack.AbstractXMPPConnection;
import org.jivesoftware.smack.ConnectionConfiguration;
import org.jivesoftware.smack.chat2.Chat;
import org.jivesoftware.smack.chat2.ChatManager;
import org.jivesoftware.smack.tcp.XMPPTCPConnection;
import org.jivesoftware.smack.tcp.XMPPTCPConnectionConfiguration;
import org.jxmpp.jid.EntityBareJid;
import org.jxmpp.jid.impl.JidCreate;

import java.util.Base64;

public class XMPPProducer {
    public static void run(String host, int size, double rate, int duration, String qos) {
        try {
            int qosLevel = Integer.parseInt(qos);

            XMPPTCPConnectionConfiguration config = XMPPTCPConnectionConfiguration.builder()
                    .setUsernameAndPassword("producer", "password")
                    .setXmppDomain("lpwan.local")
                    .setHost(host)
                    .setPort(5222)
                    .setSecurityMode(ConnectionConfiguration.SecurityMode.disabled)
                    .setConnectTimeout(15000)  // 15 second connection timeout
                    .build();

            AbstractXMPPConnection connection = new XMPPTCPConnection(config);
            connection.connect();
            connection.login();

            ChatManager chatManager = ChatManager.getInstanceFor(connection);
            EntityBareJid jid = JidCreate.entityBareFrom("subscriber@lpwan.local");
            Chat chat = chatManager.chatWith(jid);

            System.out.println("XMPP Producer Started (QoS " + qosLevel + ")");

            int count = (int) (rate * duration);
            long intervalNs = (long) ((1.0 / rate) * 1_000_000_000.0);

            for (int i = 0; i < count; i++) {
                long start = System.nanoTime();

                byte[] payload = Payload.generate(i, size);
                String encoded = Base64.getEncoder().encodeToString(payload);

                // QoS 0: Fire and forget (no wait)
                // QoS 1: Wait for send completion
                // QoS 2: Wait for send completion (same as QoS 1 for XMPP)
                if (qosLevel == 0) {
                    chat.send(encoded);
                } else {
                    // For QoS 1 and 2, we ensure the message is sent before continuing
                    chat.send(encoded);
                    Thread.sleep(1); // Small delay to ensure delivery
                }

                long elapsed = System.nanoTime() - start;
                if (intervalNs > elapsed) {
                    long sleepNs = intervalNs - elapsed;
                    long sleepMs = sleepNs / 1_000_000;
                    int sleepNano = (int) (sleepNs % 1_000_000);
                    Thread.sleep(sleepMs, sleepNano);
                }
            }

            System.out.println("BENCHMARK_SENT_COUNT=" + count);
            System.out.println("Waiting for pending messages...");
            Thread.sleep(5000);
            connection.disconnect();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
