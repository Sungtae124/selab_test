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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class SnippetGen {
    public static class MethodDeclarationInfo {
        private String name;
        private boolean is_bug = true;
        private String src_path;
        private String class_name;
        private String signature;
        private String snippet;
        private int begin_line;
        private int end_line;
        private String comment;
        private resolved_comments resolved_comments = new resolved_comments();
        private susp susp = new susp();
        private int num_failing_tests = 0;

        public MethodDeclarationInfo(String name, String filePath, String className, String signature, String snippet, int beginLine, int endLine, String comment) {
            this.name = name;
            this.src_path = filePath;
            this.class_name = className;
            this.signature = signature;
            this.snippet = snippet;
            this.begin_line = beginLine;
            this.end_line = endLine;
            this.comment = comment;
        }
    }

    public static class resolved_comments {
    }

    public static class susp {
        private double ochiai_susp = 0.5;
    }

    public List<MethodDeclarationInfo> parse(String unitName, String[] classPath, String[] sourcePath, String source) { // String sourceCode, String filePath
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

        List<MethodDeclarationInfo> methods = new ArrayList<>();

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

                String comment = node.getJavadoc() != null ? node.getJavadoc().toString() : "";
                String snippet = source.substring(node.getStartPosition(), node.getName().getStartPosition()).replaceAll("(?s)/\\*.*?\\*/|//.*", "").trim() + " " + source.substring(node.getName().getStartPosition(), node.getStartPosition() + node.getLength()); // 주석 제거

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

                methods.add(new MethodDeclarationInfo(name, unitName, className, signature, snippet, rawBeginLine, endLine, comment));
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

    public void saveAsJson(List<MethodDeclarationInfo> declarations, String outputFilePath) {
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

            String sourcePath = pathMap.get("sourceRootPath");
            String coveragePath = pathMap.get("coverage");

            // JSON 파일을 문자열로 읽기
            String content = new String(Files.readAllBytes(Paths.get(basePath, coveragePath)));

            // 문자열을 JSONObject로 변환
            JSONObject jsonObject = new JSONObject(content);

            // 값 추출
            JSONArray classes = jsonObject.getJSONArray("classes");

            List<MethodDeclarationInfo> declarations = new ArrayList<>();
            SnippetGen parser = new SnippetGen();
            String outputJsonFilePath = "rst/" + bugId.replace('-', '_') + "/snippet.json";


            for (Object cl : classes) {
                String parserUnitName = cl.toString().replace(".", "/") + ".java"; // org/apache/commons/lang3/StringUtils.java
                String sourceFilePath = basePath + sourcePath + "/" + parserUnitName; // src/main/resources/Lang-20/buggy/src/main/java/org/apache/commons/lang3/StringUtils.java
                String parserClassPath = basePath + bugId + "/lib/ " + bugId + "_buggy_src.jar"; // src/main/resources/Lang-20/lib/Lang-20_buggy_src.jar
                String parserSourcePath = basePath + sourcePath;
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
