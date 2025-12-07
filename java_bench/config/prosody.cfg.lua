admins = { }

pidfile = "/var/run/prosody/prosody.pid"

modules_enabled = {
    "roster";
    "saslauth";
    "tls";
    "dialback";
    "disco";
    "posix";
    "private";
    "vcard";
    "ping";
    "register";
    "admin_adhoc";
}

modules_disabled = {
}

allow_registration = true

c2s_require_encryption = false
s2s_require_encryption = false
s2s_secure_auth = false

authentication = "internal_plain"

log = {
    info = "*syslog";
}

VirtualHost "lpwan.local"
    enabled = true
