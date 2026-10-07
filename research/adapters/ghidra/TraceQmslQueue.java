// File-only trace of pinned QMSL FastConnect 6.1.48.1 / 6.1.365.1 x86 images.
// RVAs are explicit, build-specific evidence inputs; never reuse them across builds.
// Output must be a NEW private directory. Does not load or invoke vendor code.
// Arguments: output directory, then 1-32 explicit hexadecimal RVAs.
// Require receipt failures=0, no truncation and WHT_TRACE_OK; process exit alone is insufficient.
// @category WiFiHardwareTime

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;

public class TraceQmslQueue extends GhidraScript {
    private static final String SHA256_48 =
        "e3db8a1d93ba762a9929604c37d9d45591187a6a1eae15cc29abb22505c71dd3";
    private static final String SHA256_365 =
        "437efd33f33b64295375a1f44b272704ee3902a8c908b8147b7de7ba5988f15e";

    @Override
    public void run() throws Exception {
        String sha256 = currentProgram == null ? null : currentProgram.getExecutableSHA256();
        String build = SHA256_48.equalsIgnoreCase(sha256) ? "6.1.48.1" :
            SHA256_365.equalsIgnoreCase(sha256) ? "6.1.365.1" : null;
        if (currentProgram == null || build == null ||
            !"x86:LE:32:default".equals(currentProgram.getLanguageID().toString()) ||
            !"windows".equals(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) ||
            currentProgram.getImageBase().getOffset() != 0x10000000L) {
            throw new IllegalArgumentException("Exact supported x86 QMSL image required (6.1.48.1 or 6.1.365.1)");
        }
        String[] args = getScriptArgs();
        if (args.length < 2 || args.length > 33) {
            throw new IllegalArgumentException("Usage: NEW_PRIVATE_OUTPUT_DIR followed by 1-32 hex RVAs");
        }
        String[] addresses = java.util.Arrays.copyOfRange(args, 1, args.length);
        Set<Address> seeds = new LinkedHashSet<>();
        for (String raw : addresses) {
            if (!raw.matches("[0-9a-fA-F]{1,8}")) {
                throw new IllegalArgumentException("RVA must be 1-8 hexadecimal digits without prefix");
            }
            Address address = currentProgram.getImageBase().add(Long.parseLong(raw, 16));
            if (!currentProgram.getMemory().contains(address)) {
                throw new IllegalArgumentException("RVA outside imported image");
            }
            seeds.add(address);
        }
        Path output = Path.of(args[0]).toAbsolutePath();
        Files.createDirectory(output);
        List<String> refs = new ArrayList<>();
        refs.add("target\tfrom\ttype\tcontaining_function");
        Set<Function> functions = new LinkedHashSet<>();
        for (Address seed : seeds) {
            monitor.checkCancelled();
            Function own = getFunctionContaining(seed);
            if (own != null) { functions.add(own); }
            int count = 0;
            for (Reference ref : getReferencesTo(seed)) {
                if (++count > 256) { throw new IllegalStateException("Reference bound exceeded"); }
                Function caller = getFunctionContaining(ref.getFromAddress());
                refs.add(seed + "\t" + ref.getFromAddress() + "\t" + ref.getReferenceType() +
                    "\t" + (caller == null ? "data_or_unresolved" : caller.getEntryPoint()));
                if (caller != null) { functions.add(caller); }
            }
        }
        if (functions.isEmpty()) { throw new IllegalStateException("No functions resolved from the seeds"); }
        if (functions.size() > 96) { throw new IllegalStateException("Function bound exceeded"); }
        Files.write(output.resolve("xrefs.tsv"), refs, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW);
        List<String> receipt = new ArrayList<>();
        receipt.add("sha256\t" + sha256);
        receipt.add("image_version\t" + build);
        receipt.add("scope\tone reference level from explicit seeds; no exhaustive indirect-call proof");
        receipt.add("entry\tname\tdecompilation\tinstruction_export");
        int failures = 0;
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) {
                throw new IllegalStateException(decompiler.getLastMessage());
            }
            for (Function function : functions) {
                monitor.checkCancelled();
                String stem = function.getEntryPoint().toString();
                List<String> assembly = new ArrayList<>();
                InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
                while (instructions.hasNext() && assembly.size() < 4096) {
                    Instruction ins = instructions.next();
                    assembly.add(ins.getAddress() + "\t" + java.util.HexFormat.of().formatHex(ins.getBytes()) + "\t" + ins);
                }
                String assemblyStatus = instructions.hasNext() ? "truncated_at_4096" : "complete";
                if (instructions.hasNext()) { failures++; }
                Files.write(output.resolve(stem + ".asm.txt"), assembly, StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW);
                DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
                String status = "failed";
                if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    Files.writeString(output.resolve(stem + ".c.txt"),
                        "/* OFFLINE approximate C, not vendor source or runtime evidence. */\n" +
                        result.getDecompiledFunction().getC(), StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE_NEW);
                    status = "completed";
                } else {
                    failures++;
                    printerr(stem + ": " + result.getErrorMessage());
                }
                receipt.add(stem + "\t" + function.getName() + "\t" + status + "\t" + assemblyStatus);
            }
        } finally { decompiler.dispose(); }
        receipt.add("failures\t" + failures);
        Files.write(output.resolve("receipt.tsv"), receipt, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW);
        if (failures != 0) { throw new IllegalStateException("Incomplete decompilation or instruction export; inspect receipt"); }
        println("WHT_TRACE_OK build=" + build + " functions=" + functions.size() + " seeds=" + seeds.size());
    }
}
