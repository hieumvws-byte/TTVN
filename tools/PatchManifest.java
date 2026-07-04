import com.reandroid.arsc.chunk.xml.AndroidManifestBlock;
import com.reandroid.arsc.chunk.xml.ResXmlAttribute;
import com.reandroid.arsc.chunk.xml.ResXmlElement;

import java.io.File;
import java.nio.file.Files;
import java.util.Iterator;

// Vá manifest của base.apk để cài độc lập không cần split:
//  - bỏ isSplitRequired / requiredSplitTypes / splitTypes
//  - bật extractNativeLibs=true (lib nén trong APK vẫn cài được)
public class PatchManifest {
    static final int ID_extractNativeLibs = 0x010104ea;

    public static void main(String[] args) throws Exception {
        AndroidManifestBlock manifest = AndroidManifestBlock.load(new File(args[0]));

        ResXmlElement man = manifest.getManifestElement();
        ResXmlElement app = manifest.getApplicationElement();

        System.out.println("== manifest attrs (trước):");
        dump(man);
        System.out.println("== application attrs (trước):");
        dump(app);

        man.removeAttributesWithId(0x0101064e);  // requiredSplitTypes
        man.removeAttributesWithId(0x0101064f);  // splitTypes
        man.removeAttributesWithName("requiredSplitTypes");
        man.removeAttributesWithName("splitTypes");
        app.removeAttributesWithId(0x01010591);  // isSplitRequired
        app.removeAttributesWithName("isSplitRequired");
        boolean stillThere = man.searchAttributeByResourceId(0x0101064e) != null
            || man.searchAttributeByResourceId(0x0101064f) != null;
        if (stillThere) throw new IllegalStateException("Chưa xóa được cờ split!");

        ResXmlAttribute ext = app.getOrCreateAndroidAttribute(
            "extractNativeLibs", ID_extractNativeLibs);
        ext.setValueAsBoolean(true);

        manifest.refresh();
        Files.write(new File(args[1]).toPath(), manifest.getBytes());

        System.out.println("== application attrs (sau):");
        dump(app);
        System.out.println("OK -> " + args[1]);
    }

    static void dump(ResXmlElement el) {
        Iterator<ResXmlAttribute> it = el.getAttributes();
        while (it.hasNext()) {
            ResXmlAttribute a = it.next();
            System.out.printf("  %s (0x%08x) = %s%n",
                a.getName(), a.getNameId(), a.getValueAsString());
        }
    }
}
