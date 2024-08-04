package kr.ac.seoultech.selab;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.dom.*;
import org.json.*;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;

public class TestSnippetGen {
    public static class TestDeclarationInfo {
        private String class_name;
        private List<String> child_classes = new ArrayList<>();
        private String src_path;
        private String signature;
        private String snippet;
        private int begin_line;
        private int end_line;
        private String comment;
        private List<String> child_ranges;

        public TestDeclarationInfo(String name, String filePath, String className, String signature, String snippet, int beginLine, int endLine, String comment, List<String> childRanges) {
            this.class_name = name;
            this.src_path = filePath;
            this.class_name = className;
            this.signature = signature;
            this.snippet = snippet;
            this.begin_line = beginLine;
            this.end_line = endLine;
            this.comment = comment;
            this.child_ranges = childRanges;
        }
    }

    public List<TestDeclarationInfo> parse(String unitName, String[] classPath, String[] sourcePath, String source) { // String sourceCode, String filePath
        ASTParser parser = ASTParser.newParser(AST.getJLSLatest());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        Map<String, String> options = JavaCore.getOptions();
        JavaCore.setComplianceOptions(JavaCore.latestSupportedJavaVersion(), options);
        parser.setCompilerOptions(options);
        parser.setEnvironment(classPath, sourcePath, null, true);
        parser.setUnitName(unitName);
        parser.setResolveBindings(true);
        parser.setSource(source.toCharArray());
        CompilationUnit cu = (CompilationUnit) parser.createAST(null);

        List<TestDeclarationInfo> methods = new ArrayList<>();

        cu.accept(new ASTVisitor() {
            private String currentClassName = null;

            @Override
            public boolean visit(TypeDeclaration node) {
                currentClassName = node.getName().getFullyQualifiedName();
                return super.visit(node);
            }

            @Override
            public boolean visit(MethodDeclaration node) {
                int rawBeginLine = cu.getLineNumber(node.getName().getStartPosition());
                int endLine = cu.getLineNumber(node.getStartPosition() + node.getLength());

                String rawSnippet = node.toString().trim();
                String comment = node.getJavadoc() != null ? node.getJavadoc().toString() : "";
                String snippet = rawSnippet.replaceAll("(?s)/\\*.*?\\*/|//.*", "").trim(); // 주석 제거

                String methodName = node.getName().getFullyQualifiedName();

                List<String> paramTypes = new ArrayList<>();
                List<SingleVariableDeclaration> parameters = node.parameters();
                for (SingleVariableDeclaration parameter : parameters) {
                    Type type = parameter.getType();
                    String typeSignature = getTypeSignature(type);
                    if (typeSignature != null) {
                        paramTypes.add(typeSignature);
                    } else {
                        System.err.println("Failed to resolve binding for type: " + type);
                    }
                }

                String className = unitName.replace(".java", "").replace("/", ".");
                String signature = className + "." + methodName + "(" + String.join(", ", paramTypes) + ")";
                String name = currentClassName + "." + methodName + "#" + rawBeginLine;

                // Extract child ranges
                List<String> childRanges = new ArrayList<>();
                Block body = node.getBody();
                if (body != null) {
                    for (Statement statement : (List<Statement>) body.statements()) {
                        int startLine = cu.getLineNumber(statement.getStartPosition());
                        int endLineStmt = cu.getLineNumber(statement.getStartPosition() + statement.getLength());
                        int startCol = cu.getColumnNumber(statement.getStartPosition()) + 1;
                        int endCol = cu.getColumnNumber(statement.getStartPosition() + statement.getLength());
                        childRanges.add("(line " + startLine + ",col " + startCol + ")-(line " + endLineStmt + ",col " + endCol + ")");
                    }
                }

                methods.add(new TestDeclarationInfo(name, unitName, className, signature, snippet, rawBeginLine, endLine, comment, childRanges));
                return super.visit(node);
            }

            private String getTypeSignature(Type type) {
                ITypeBinding tb = (ITypeBinding) type.resolveBinding();
                if (tb != null) {
                    if (tb.isPrimitive()) {
//                        System.out.println("Primitive type: " + tb.getName());
                        return tb.getName();
                    }
//
//                    if (tb.isArray()) {
//                        //Handle array type.
//                        System.out.println("Array type: " + tb.getQualifiedName());
//                    }
//
//                    if (tb.isParameterizedType()) {
//                        //Handle parameterized type.
//                        System.out.println("Parameterized type: " + tb.getQualifiedName());
//                    }

                    //Handle other special cases...

                    //Otherwise, returns the qualified name.
                    return tb.getQualifiedName();
                }
//                System.out.println("Failed to resolve binding for type: " + type);
                return type.toString(); // or throw an exception if tb is null
            }
        });

        return methods;
    }

    public void saveAsJson(List<TestDeclarationInfo> declarations, String outputFilePath) {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        try (FileWriter writer = new FileWriter(outputFilePath)) {
            gson.toJson(declarations, writer);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) throws IOException {

        PathAssembler pathAssembler = new PathAssembler();
        for (String bugId : pathAssembler.defects4j) {

            String basePath = "src/main/resources/";
            Map<String, String> pathMap = pathAssembler.assembler(bugId);

            String npeTracesJsonPath = pathMap.get("jsonFilePath");
            String testPath = pathMap.get("testRootPath");

            // JSON 파일을 문자열로 읽기
            String npeTracesJson = new String(Files.readAllBytes(Paths.get(basePath, npeTracesJsonPath)));

            // 문자열을 JSONObject로 변환
            JSONObject jsonObject = new JSONObject(npeTracesJson);

            // 값 추출
            JSONArray npeTraces = jsonObject.getJSONArray("npe.traces");
            Set<String> testClasses = new HashSet<>();
            for (Object npeTrace : npeTraces) {
                JSONObject npeTraceObj = (JSONObject) npeTrace;
                String className = npeTraceObj.getString("test.class");
                testClasses.add(className);
            }
            List<TestDeclarationInfo> declarations = new ArrayList<>();
            TestSnippetGen parser = new TestSnippetGen();
            String outputJsonFilePath = "rst/" + bugId.replace('-', '_') + "/test_snippet.json";


            for (Object cl : testClasses) {
                String parserUnitName = cl.toString().replace(".", "/") + ".java"; // org/apache/commons/lang3/StringUtils.java
                String sourceFilePath = basePath + testPath + "/" + parserUnitName; // src/main/resources/Lang-20/buggy/src/main/java/org/apache/commons/lang3/StringUtils.java
                String parserClassPath = basePath + bugId + "/lib/ " + bugId + "_buggy_src.jar"; // src/main/resources/Lang-20/lib/Lang-20_buggy_src.jar
                String parserSourcePath = basePath + testPath;
                try {
                    String javaSourceCode = new String(Files.readAllBytes(Paths.get(sourceFilePath).toAbsolutePath()));
                    // String unitName, String[] classPath, String[] sourcePath, String source
                    declarations.addAll(parser.parse(parserUnitName, new String[]{parserClassPath}, new String[]{parserSourcePath}, javaSourceCode));
                } catch (java.nio.file.NoSuchFileException e) {

                } catch (Exception e) {
                    System.out.println(bugId + ")Error: " + e);
                }
            }
            parser.saveAsJson(declarations, outputJsonFilePath);
            System.out.println(declarations.size());
        }
    }
}
