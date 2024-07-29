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

public class JavaParser {
    public static class VariableDeclaration {
        public String class_name;
        public String src_path;
        public String signature;
        public String snippet;
        public int begin_line;
        public int end_line;
        public String comment;

        public VariableDeclaration(String class_name, String src_path, String signature, String snippet, int begin_line, int end_line, String comment) {
            this.class_name = class_name;
            this.src_path = src_path;
            this.signature = signature;
            this.snippet = snippet;
            this.begin_line = begin_line;
            this.end_line = end_line;
            this.comment = comment;
        }
    }

    public List<VariableDeclaration> parse(String sourceCode, String filePath) {
        ASTParser parser = ASTParser.newParser(AST.getJLSLatest());
        parser.setSource(sourceCode.toCharArray());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);

        CompilationUnit cu = (CompilationUnit) parser.createAST(null);

        List<VariableDeclaration> declarations = new ArrayList<>();

        cu.accept(new ASTVisitor() {
            private String currentClassName = null;

            @Override
            public boolean visit(TypeDeclaration node) {
                currentClassName = node.getName().getFullyQualifiedName();
                return super.visit(node);
            }

            @Override
            public boolean visit(FieldDeclaration node) {
                int rawBeginLine = cu.getLineNumber(node.getStartPosition());
                int rawEndLine = cu.getLineNumber(node.getStartPosition() + node.getLength());

                String rawSnippet = node.toString().trim();
                String comment = node.getJavadoc() != null ? node.getJavadoc().toString() : "";
                String snippet = rawSnippet.replaceAll("(?s)/\\*.*?\\*/|//.*", "").trim(); // 주석 제거

                // 주석 제거 후 실제 선언부의 시작 라인을 찾기 위해 라인 단위로 나누고, 주석 제거된 라인의 인덱스를 찾음
                String[] lines = rawSnippet.split("\n");
                int offset = 0;

                for (int i = lines.length - 1; i >= 0; i--) {
                    if (lines[i].contains(snippet.split("\\s+")[0])) { // snippet의 첫 번째 단어가 포함된 라인 찾기
                        break;
                    }
                    offset++;
                }

                int beginLine = rawEndLine - offset;

                for (Object fragment : node.fragments()) {
                    VariableDeclarationFragment vdf = (VariableDeclarationFragment) fragment;
                    String variableName = vdf.getName().getFullyQualifiedName();
                    String signature = currentClassName + "." + variableName;
                    declarations.add(new VariableDeclaration(currentClassName, filePath, signature, snippet, beginLine, rawEndLine, comment));
                }
                return super.visit(node);
            }
        });

        return declarations;
    }

    public void saveAsJson(List<VariableDeclaration> declarations, String outputFilePath) {
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

            List<VariableDeclaration> declarations = new ArrayList<>();
            JavaParser parser = new JavaParser();
            String outputJsonFilePath = "field_snippet/" + bugId + ".json";


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
