import com.android.apksig.ApkSigner;
import com.android.apksig.ApkVerifier;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class SignApk {
    public static void main(String[] args) throws Exception {
        String ksPath = args[0], pass = args[1], alias = args[2];
        String in = args[3], out = args[4];

        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (InputStream is = new FileInputStream(ksPath)) {
            ks.load(is, pass.toCharArray());
        }
        PrivateKey pk = (PrivateKey) ks.getKey(alias, pass.toCharArray());
        List<X509Certificate> certs = new ArrayList<>();
        for (java.security.cert.Certificate c : ks.getCertificateChain(alias)) {
            certs.add((X509Certificate) c);
        }

        ApkSigner.SignerConfig sc =
            new ApkSigner.SignerConfig.Builder("TTVN", pk, certs).build();
        new ApkSigner.Builder(Collections.singletonList(sc))
            .setInputApk(new File(in))
            .setOutputApk(new File(out))
            .setV1SigningEnabled(false)
            .setV2SigningEnabled(true)
            .build()
            .sign();

        ApkVerifier.Result r = new ApkVerifier.Builder(new File(out)).build().verify();
        System.out.println("signed=" + out
            + " verified=" + r.isVerified()
            + " v1=" + r.isVerifiedUsingV1Scheme()
            + " v2=" + r.isVerifiedUsingV2Scheme());
        if (!r.isVerified()) {
            for (ApkVerifier.IssueWithParams e : r.getErrors()) System.out.println("ERR: " + e);
            System.exit(1);
        }
    }
}
