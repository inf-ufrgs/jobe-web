#!/bin/bash
# Generate SP Certificate and Private Key for SAML authentication
# These files will be used by the SAML SP (jobe-web) to sign requests
# and decrypt assertions from the UFRGS IdP.
#
# Usage: ./scripts/generate-sp-certs.sh [output_dir]
# Default output: ./grader/saml/certs/

set -e

OUTPUT_DIR="${1:-./grader/saml/certs}"

mkdir -p "$OUTPUT_DIR"

echo "🔐 Generating SP Certificate and Private Key..."
echo ""

# Create OpenSSL config
cat > /tmp/saml-openssl.cnf << 'EOF'
[ req ]
default_bits       = 2048
string_mask        = nombstr
distinguished_name = req_distinguished_name
prompt             = no

[ req_distinguished_name ]
C  = BR
ST = Rio Grande do Sul
L  = Porto Alegre
O  = UFRGS - Universidade Federal do Rio Grande do Sul
OU = INF - Instituto de Informatica
CN = jobe-web.k8s.inf.ufrgs.br
EOF

# Generate private key and self-signed certificate (valid for 3 years)
openssl req \
    -new -x509 -nodes \
    -days 1095 \
    -sha256 \
    -newkey rsa:2048 \
    -keyout "$OUTPUT_DIR/sp.key" \
    -out "$OUTPUT_DIR/sp.crt" \
    -config /tmp/saml-openssl.cnf

# Clean up
rm -f /tmp/saml-openssl.cnf

echo ""
echo "✅ Files generated:"
echo "   Certificate: $OUTPUT_DIR/sp.crt"
echo "   Private Key: $OUTPUT_DIR/sp.key"
echo ""
echo "📋 Next steps:"
echo "   1. Start the app with SAML_ENABLED=true"
echo "   2. Visit /saml/metadata to get the SP metadata XML"
echo "   3. Send the metadata XML to rui.ribeiro@cpd.ufrgs.br"
echo "   4. Store sp.crt and sp.key as Kubernetes Secrets (see kubernetes/saml-secrets.yaml)"
echo ""
echo "⚠️  IMPORTANT: Do NOT commit sp.key to Git!"
