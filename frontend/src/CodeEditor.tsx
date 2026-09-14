import Editor, { loader } from "@monaco-editor/react";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";

loader.config({ monaco });

const monacoGlobal = globalThis as typeof globalThis & {
  MonacoEnvironment?: { getWorker: () => Worker };
};

monacoGlobal.MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
};

export default function PythonEditor({ value, onChange, ariaLabel }: { value: string; onChange: (value: string) => void; ariaLabel: string }) {
  return (
    <div className="monaco-shell" dir="ltr">
      <Editor
        height="100%"
        language="python"
        path="solution.py"
        value={value}
        onChange={(nextValue) => onChange(nextValue ?? "")}
        theme="vs-dark"
        options={{
          accessibilitySupport: "on",
          ariaLabel,
          automaticLayout: true,
          fontFamily: '"Cascadia Code", Consolas, monospace',
          fontSize: 14,
          lineHeight: 22,
          minimap: { enabled: false },
          padding: { top: 14, bottom: 14 },
          renderLineHighlight: "line",
          scrollBeyondLastLine: false,
          tabSize: 4,
          wordWrap: "on",
        }}
      />
    </div>
  );
}
