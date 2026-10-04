// Export bounded, offline function/caller evidence from the exact owned image.
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

public class TraceQualcommPacketlog extends GhidraScript {
    private static final String SHA256 =
        "ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115";

    @Override
    public void run() throws Exception {
        if (currentProgram == null || !SHA256.equalsIgnoreCase(currentProgram.getExecutableSHA256()) ||
            !"AARCH64:LE:64:v8A".equals(currentProgram.getLanguageID().toString()) ||
            !"windows".equals(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) ||
            currentProgram.getImageBase().getOffset() != 0x140000000L) {
            throw new IllegalArgumentException("Exact ARM64 Windows image/hash/base required");
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
        if (functions.size() > 96) { throw new IllegalStateException("Function bound exceeded"); }
        Files.write(output.resolve("xrefs.tsv"), refs, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW);
        List<String> receipt = new ArrayList<>();
        receipt.add("sha256\t" + SHA256);
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
                Files.write(output.resolve(stem + ".asm.txt"), assembly, StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW);
                DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
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
        if (failures != 0) { throw new IllegalStateException("Incomplete decompilation; inspect receipt"); }
        println("WHT_TRACE_OK functions=" + functions.size() + " seeds=" + seeds.size());
    }
}
