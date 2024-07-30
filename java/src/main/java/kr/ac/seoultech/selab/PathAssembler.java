package kr.ac.seoultech.selab;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class PathAssembler {

    List<String> googleSheet = new ArrayList<>();

    List<String> defects4j = new ArrayList<>();

    //일단 하드코딩으로... 경로 주기
    public PathAssembler() {
//        googleSheet.add("lang_npe_1");
//        googleSheet.add("lang_npe_2");
//        googleSheet.add("lang_npe_3");
//        googleSheet.add("lang_npe_4");
//        googleSheet.add("lang_npe_5");
//        googleSheet.add("lang_npe_6");
//        googleSheet.add("lang_npe_7");
//        googleSheet.add("lang_npe_8");
//        googleSheet.add("lang_npe_9");
//        googleSheet.add("lang_npe_10");
//        googleSheet.add("lang_npe_11");
//        googleSheet.add("lang_npe_12");
//        googleSheet.add("lang_npe_13");
//        googleSheet.add("lang_npe_14");
//        googleSheet.add("math_npe_1");
//        googleSheet.add("math_npe_2");
//        googleSheet.add("math_npe_3");
//        googleSheet.add("math_npe_4");
//        googleSheet.add("math_npe_5");
//        googleSheet.add("math_npe_6");
//        googleSheet.add("collections_npe_1");
//        googleSheet.add("collections_npe_2");
//        googleSheet.add("collections_npe_3");
//        googleSheet.add("commons-io_npe_1");
//        googleSheet.add("commons-io_npe_2");
//        googleSheet.add("commons-io_npe_3");
//        googleSheet.add("commons-io_npe_4");
//        googleSheet.add("commons-io_npe_6");
//        googleSheet.add("commons-io_npe_7");
//        googleSheet.add("commons-io_npe_8");
//        googleSheet.add("commons-io_npe_10");
//        googleSheet.add("commons-io_npe_11");
//        googleSheet.add("commons-io_npe_12");
//        googleSheet.add("commons-io_npe_13");
//        googleSheet.add("commons-io_npe_14");
//        googleSheet.add("commons-io_npe_15");
//        googleSheet.add("commons-io_npe_16");
//        googleSheet.add("commons-io_npe_17");
//        googleSheet.add("commons-io_npe_18");
//        googleSheet.add("commons-io_npe_19");

        // no test code snippet
//        googleSheet.add("commons-io_npe_5");
//        googleSheet.add("commons-io_npe_9");



        // defects4j
        defects4j.add("Chart-2");
        defects4j.add("Chart-4");
        defects4j.add("Chart-14");
        defects4j.add("Chart-16");
        defects4j.add("Cli-5");
        defects4j.add("Cli-30");
        defects4j.add("Closure-2");
        defects4j.add("Closure-171");
        defects4j.add("Codec-5");
        defects4j.add("Codec-13");
        defects4j.add("Codec-17");
        defects4j.add("Csv-4");
        defects4j.add("Csv-9");
        defects4j.add("Csv-11");
        defects4j.add("Gson-6");
        defects4j.add("Gson-9");
        defects4j.add("JacksonCore-8");
        defects4j.add("JacksonDatabind-3");
        defects4j.add("JacksonDatabind-13");
        defects4j.add("JacksonDatabind-36");
        defects4j.add("JacksonDatabind-80");
        defects4j.add("JacksonDatabind-93");
        defects4j.add("JacksonDatabind-95");
        defects4j.add("JacksonDatabind-107");
        defects4j.add("Jsoup-8");
        defects4j.add("Jsoup-22");
        defects4j.add("Jsoup-26");
        defects4j.add("Jsoup-66");
        defects4j.add("Jsoup-89");
        defects4j.add("Lang-20");
        defects4j.add("Lang-33");
        defects4j.add("Lang-39");
        defects4j.add("Lang-47");
        defects4j.add("Lang-57");
        defects4j.add("Math-4");
        defects4j.add("Math-70");
        defects4j.add("Math-79");
        defects4j.add("Mockito-18");
        defects4j.add("Mockito-38");

        // no code snippet
//        defects4j.add("Chart-2");
//        defects4j.add("Closure-171");
//        defects4j.add("Gson-9");
//        defects4j.add("JacksonCore-8");
//        defects4j.add("JacksonDatabind-36");
//        defects4j.add("Jsoup-66");
//        defects4j.add("JxPath-1");
//        defects4j.add("Mockito-4");
//        defects4j.add("Mockito-18");
//        defects4j.add("Mockito-29");
//        defects4j.add("Mockito-36");
        // no test code snippet
//        defects4j.add("Cli-30");
//        defects4j.add("Closure-2");
//        defects4j.add("Gson-6");
//        defects4j.add("Lang-57");
    }


    public Map<String, String> assembler(String name) {
        Map<String, String> fullPath = new HashMap<>(); //jsonFilePath , sourceRootPath , testRootPath
        if (googleSheet.contains(name)) {
            fullPath.put("jsonFilePath", name + "/npe.traces.json");
            fullPath.put("sourceRootPath", name + "/buggy/src/main/java");
            fullPath.put("testRootPath", name + "/fixed/src/test/java");
            fullPath.put("stackTraces", name + "/stack_traces.txt");
        } else {
            switch (name) {
                case "Chart-2":
                case "Chart-4":
                case "Chart-14":
                case "Chart-16":
                    fullPath.put("testRootPath", name + "/fixed/tests");
                    break;
                case "Cli-5":
                case "Codec-5":
                case "JxPath-1":
                case "Lang-39":
                case "Lang-47":
                case "Lang-57":
                    fullPath.put("testRootPath", name + "/fixed/src/test");
                    break;
                case "Closure-2":
                case "Closure-171":
                case "Mockito-4":
                case "Mockito-18":
                case "Mockito-29":
                case "Mockito-36":
                case "Mockito-38":
                    fullPath.put("testRootPath", name + "/fixed/test");
                    break;
                case "Gson-6":
                case "Gson-9":
                    fullPath.put("testRootPath", name + "/fixed/gson/src/test/java");
                    break;
                default:
                    fullPath.put("testRootPath", name + "/fixed/src/test/java");
                    break;
            }
            fullPath.put("jsonFilePath", name + "/npe.traces.json");
            ConfigReader configReader = new ConfigReader(name + "/config.properties");
            String sourcePath = configReader.getProperty("source.path");
            if (sourcePath.contains(":")) {
                sourcePath = sourcePath.substring(0, sourcePath.indexOf(":"));
            }
            fullPath.put("sourceRootPath", name + "/" + sourcePath);
            fullPath.put("stackTraces", name + "/stack_traces.txt");
            fullPath.put("coverage", name + "/coverage.json");
        }
        return fullPath;
    }
}
