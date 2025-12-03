package com.lpwan.bench.common;

import java.nio.ByteBuffer;
import java.util.Random;

public class Payload {
    
    public static byte[] generate(long seq, int size) {
        if (size < 16) size = 16;
        
        byte[] payload = new byte[size];
        ByteBuffer buffer = ByteBuffer.wrap(payload);
        
        // Metadata (16 Byte)
        buffer.putLong(seq);
        buffer.putDouble(System.currentTimeMillis() / 1000.0); // Timestamp (seconds)
        
        // Padding
        Random rand = new Random();
        for (int i = 16; i < size; i++) {
            payload[i] = (byte) rand.nextInt(256);
        }
        
        return payload;
    }
    
    public static ParsedPayload parse(byte[] data) {
        if (data == null || data.length < 16) return null;
        
        ByteBuffer buffer = ByteBuffer.wrap(data);
        long seq = buffer.getLong();
        double timestamp = buffer.getDouble();
        
        double now = System.currentTimeMillis() / 1000.0;
        double latencyMs = (now - timestamp) * 1000.0;
        
        return new ParsedPayload(seq, timestamp, latencyMs);
    }
    
    public static class ParsedPayload {
        public long seq;
        public double timestamp;
        public double latencyMs;
        
        public ParsedPayload(long seq, double timestamp, double latencyMs) {
            this.seq = seq;
            this.timestamp = timestamp;
            this.latencyMs = latencyMs;
        }
    }
}
