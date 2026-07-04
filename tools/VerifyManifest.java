import com.reandroid.arsc.chunk.xml.AndroidManifestBlock;
import com.reandroid.arsc.chunk.xml.ResXmlAttribute;
import java.io.File;
import java.util.Iterator;

public class VerifyManifest {
    public static void main(String[] args) throws Exception {
        AndroidManifestBlock m = AndroidManifestBlock.load(new File(args[0]));
        System.out.println("manifest attrs:");
        Iterator<ResXmlAttribute> it = m.getManifestElement().getAttributes();
        while (it.hasNext()) System.out.println("  " + it.next().getName());
        ResXmlAttribute ext = m.getApplicationElement()
            .searchAttributeByResourceId(0x010104ea);
        System.out.println("extractNativeLibs = " + (ext == null ? "MISSING" : ext.getValueAsBoolean()));
        System.out.println("package = " + m.getPackageName());
    }
}
