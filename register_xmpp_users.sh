#!/bin/bash

# Wait for XMPP server to be ready
echo "Waiting for XMPP server to start..."
sleep 10

# Register users
echo "Registering XMPP users..."

docker exec xmpp-server ejabberdctl register producer lpwan.local password
docker exec xmpp-server ejabberdctl register subscriber lpwan.local password

echo "XMPP users registered successfully!"
echo "  - producer@lpwan.local (password: password)"
echo "  - subscriber@lpwan.local (password: password)"

# Check registered users
echo ""
echo "Registered users:"
docker exec xmpp-server ejabberdctl registered_users lpwan.local
