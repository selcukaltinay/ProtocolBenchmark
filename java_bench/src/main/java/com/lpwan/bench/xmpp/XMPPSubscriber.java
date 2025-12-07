package com.lpwan.bench.xmpp;

import com.lpwan.bench.common.Payload;
import org.jivesoftware.smack.AbstractXMPPConnection;
import org.jivesoftware.smack.ConnectionConfiguration;
import org.jivesoftware.smack.chat2.Chat;
import org.jivesoftware.smack.chat2.ChatManager;
import org.jivesoftware.smack.chat2.IncomingChatMessageListener;
import org.jivesoftware.smack.packet.Message;
import org.jivesoftware.smack.tcp.XMPPTCPConnection;
import org.jivesoftware.smack.tcp.XMPPTCPConnectionConfiguration;
import org.jxmpp.jid.EntityBareJid;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

public class XMPPSubscriber {
    private static List<Payload.ParsedPayload> results = new ArrayList<>();

    public static void run(String host, String qos) {
        try {
            int qosLevel = Integer.parseInt(qos);

            XMPPTCPConnectionConfiguration config = XMPPTCPConnectionConfiguration.builder()
                    .setUsernameAndPassword("subscriber", "password")
                    .setXmppDomain("lpwan.local")
                    .setHost(host)
                    .setPort(5222)
                    .setSecurityMode(ConnectionConfiguration.SecurityMode.disabled)
                    .build();

            AbstractXMPPConnection connection = new XMPPTCPConnection(config);
            connection.connect();
            connection.login();

            ChatManager chatManager = ChatManager.getInstanceFor(connection);
            chatManager.addIncomingListener(new IncomingChatMessageListener() {
                @Override
                public void newIncomingMessage(EntityBareJid from, Message message, Chat chat) {
                    String body = message.getBody();
                    if (body != null) {
                        try {
                            byte[] payload = Base64.getDecoder().decode(body);
                            Payload.ParsedPayload p = Payload.parse(payload);
                            if (p != null) {
                                synchronized (results) {
                                    results.add(p);
                                }
                            }
                        } catch (Exception e) {
                            // Ignore malformed
                        }
                    }
                }
            });

            System.out.println("XMPP Subscriber Started (QoS " + qosLevel + ")");

            // Wait indefinitely
            synchronized (XMPPSubscriber.class) {
                XMPPSubscriber.class.wait();
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
