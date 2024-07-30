package kr.ac.seoultech.selab;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
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

    public List<MethodDeclarationInfo> parse(String sourceCode, String filePath) {
        ASTParser parser = ASTParser.newParser(AST.getJLSLatest());
        parser.setSource(sourceCode.toCharArray());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);

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
                int rawBeginLine = cu.getLineNumber(node.getStartPosition());
                int endLine = cu.getLineNumber(node.getStartPosition() + node.getLength());

                String rawSnippet = node.toString().trim();
                String comment = node.getJavadoc() != null ? node.getJavadoc().toString() : "";
                String snippet = rawSnippet.replaceAll("(?s)/\\*.*?\\*/|//.*", "").trim(); // 주석 제거

                String methodName = node.getName().getFullyQualifiedName();


                // 주석 제거 후 실제 선언부의 시작 라인을 찾기 위해 라인 단위로 나누고, 주석 제거된 라인의 인덱스를 찾음
                String[] lines = node.toString().split("\n");
                int beginLine = rawBeginLine;

                for (int i = 0; i < lines.length; i++) {
                    if (lines[i].contains(methodName)) {
                        beginLine = i + rawBeginLine;
                        break;
                    }
                }

                String className = filePath.substring(filePath.indexOf("org")).replace("/", ".").replace(".java", "");
                String signature = className + "." + methodName;
                String name = currentClassName + "." + methodName + "#" + beginLine;

                methods.add(new MethodDeclarationInfo(name, filePath.substring(filePath.indexOf("buggy/") + 6), className, signature, snippet, beginLine, endLine, comment));
                return super.visit(node);
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
            String outputJsonFilePath = "rst/" + bugId + "/snippet.json";


            for (Object cl : classes) {
                String classPath = cl.toString().replace(".", "/") + ".java";
                String sourceFilePath = basePath + sourcePath + "/" + classPath;
                try {
                    String javaSourceCode = new String(Files.readAllBytes(Paths.get(sourceFilePath).toAbsolutePath()));
                    declarations.addAll(parser.parse(javaSourceCode, sourceFilePath));
                } catch (Exception e) {
                    System.out.println("Error: " + sourceFilePath);
                }
            }
            parser.saveAsJson(declarations, outputJsonFilePath);
            System.out.println(declarations.size());
        }
    }
}