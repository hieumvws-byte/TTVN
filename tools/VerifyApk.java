import com.android.apksig.ApkVerifier;
import java.io.File;

public class VerifyApk {
    public static void main(String[] args) throws Exception {
        ApkVerifier.Result r = new ApkVerifier.Builder(new File(args[0]))
            .setMinCheckedPlatformVersion(24)  // Android 7.0+
            .build().verify();
        System.out.println(args[0] + " verified=" + r.isVerified() + " v2=" + r.isVerifiedUsingV2Scheme());
        if (!r.isVerified()) { for (var e : r.getErrors()) System.out.println("ERR: " + e); System.exit(1); }
    }
}
