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

public class FieldSnippetGen {
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

    public List<VariableDeclaration> parse(String unitName, String[] classPath, String[] sourcePath, String source) {
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
                int rawBeginLine = cu.getLineNumber(node.getType().getStartPosition());
                int rawEndLine = cu.getLineNumber(node.getStartPosition() + node.getLength());

                String comment = node.getJavadoc() != null ? node.getJavadoc().toString() : "";
                String snippet = source.substring(node.getStartPosition(), node.getType().getStartPosition()).replaceAll("(?s)/\\*.*?\\*/|//.*", "").trim() + " " + source.substring(node.getType().getStartPosition(), node.getStartPosition() + node.getLength()); // 주석 제거

                int beginLine = rawBeginLine;
                for (Object fragment : node.fragments()) {
                    VariableDeclarationFragment vdf = (VariableDeclarationFragment) fragment;
                    String variableName = vdf.getName().getFullyQualifiedName();
                    String className = unitName.replace(".java", "").replace("/", ".");
                    String signature = className + "." + variableName;
                    declarations.add(new VariableDeclaration(className, unitName, signature, snippet, beginLine, rawEndLine, comment));
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
            FieldSnippetGen parser = new FieldSnippetGen();
            String outputJsonFilePath = "rst/" + bugId.replace('-', '_') + "/field_snippet.json";

            for (Object cl : classes) {
                String parserUnitName = cl.toString().replace(".", "/") + ".java";
                String sourceFilePath = basePath + sourcePath + "/" + parserUnitName;
                String parserClassPath = basePath + bugId + "/lib/ " + bugId + "_buggy_src.jar";
                String parserSourcePath = basePath + sourcePath;
                try {
                    String javaSourceCode = new String(Files.readAllBytes(Paths.get(sourceFilePath).toAbsolutePath()));
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
