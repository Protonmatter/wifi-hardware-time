// Export bounded offline device/protocol-discovery evidence from pinned QUTS images.
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

public class TraceQutsDiscovery extends GhidraScript {
    private static final Set<String> HASHES = Set.of(
        "8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297", // QUTS.exe
        "30dc1fac9c9fb7a5672fb665daf33f72c8bc3456fa545bd169c7ae77eb4863b6"  // QUTSService.exe
    );

    @Override
    public void run() throws Exception {
        if (currentProgram == null || !HASHES.contains(currentProgram.getExecutableSHA256().toLowerCase(java.util.Locale.ROOT)) ||
            !"AARCH64:LE:64:v8A".equals(currentProgram.getLanguageID().toString()) ||
            !"windows".equals(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) ||
            currentProgram.getImageBase().getOffset() != 0x140000000L) {
            throw new IllegalArgumentException("Pinned QUTS ARM64 Windows image/hash/base required");
        }
        String[] args = getScriptArgs();
        if (args.length < 2 || args.length > 34) {
            throw new IllegalArgumentException("Usage: NEW_PRIVATE_OUTPUT_DIR [max-instructions:4096..65536] followed by 1-32 hex RVAs (entry:HEX explicitly defines a reviewed function start)");
        }
        int instructionLimit = 4096;
        int seedStart = 1;
        if (args[1].startsWith("max-instructions:")) {
            String rawLimit = args[1].substring("max-instructions:".length());
            if (!rawLimit.matches("[0-9]{4,5}")) {
                throw new IllegalArgumentException("Instruction limit must be 4096..65536");
            }
            instructionLimit = Integer.parseInt(rawLimit);
            if (instructionLimit < 4096 || instructionLimit > 65536) {
                throw new IllegalArgumentException("Instruction limit must be 4096..65536");
            }
            seedStart = 2;
        }
        if (args.length - seedStart < 1 || args.length - seedStart > 32) {
            throw new IllegalArgumentException("Supply 1-32 seeds");
        }
        String[] addresses = java.util.Arrays.copyOfRange(args, seedStart, args.length);
        Set<Address> seeds = new LinkedHashSet<>();
        Set<Address> definitions = new LinkedHashSet<>();
        for (String raw : addresses) {
            boolean define = raw.startsWith("entry:");
            if (define) { raw = raw.substring(6); }
            if (!raw.matches("[0-9a-fA-F]{1,8}")) {
                throw new IllegalArgumentException("RVA must be 1-8 hexadecimal digits without prefix");
            }
            Address address = currentProgram.getImageBase().add(Long.parseLong(raw, 16));
            if (!currentProgram.getMemory().contains(address)) {
                throw new IllegalArgumentException("RVA outside imported image");
            }
            seeds.add(address);
            if (define) { definitions.add(address); }
        }
        Path output = Path.of(args[0]).toAbsolutePath();
        Files.createDirectory(output);
        List<String> refs = new ArrayList<>();
        refs.add("target\tfrom\ttype\tcontaining_function");
        Set<Function> functions = new LinkedHashSet<>();
        for (Address seed : seeds) {
            monitor.checkCancelled();
            Function own = getFunctionContaining(seed);
            if (definitions.contains(seed)) {
                if (own != null && !own.getEntryPoint().equals(seed)) {
                    throw new IllegalArgumentException("Explicit entry overlaps an existing function");
                }
                if (own == null) {
                    if (!disassemble(seed)) { throw new IllegalStateException("Cannot disassemble reviewed entry " + seed); }
                    own = createFunction(seed, null);
                    if (own == null) { throw new IllegalStateException("Cannot define reviewed entry " + seed); }
                }
            }
            refs.add(seed + "\tseed\t" + (definitions.contains(seed) ? "explicit_entry" : "existing") +
                "\t" + (own == null ? "data_or_unresolved" : own.getEntryPoint()));
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
        if (functions.isEmpty()) { throw new IllegalStateException("No functions resolved; seed code RVAs or complete reference analysis"); }
        if (functions.size() > 96) { throw new IllegalStateException("Function bound exceeded"); }
        Files.write(output.resolve("xrefs.tsv"), refs, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW);
        List<String> receipt = new ArrayList<>();
        receipt.add("sha256\t" + currentProgram.getExecutableSHA256());
        receipt.add("instruction_limit\t" + instructionLimit);
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
                while (instructions.hasNext() && assembly.size() < instructionLimit) {
                    Instruction ins = instructions.next();
                    assembly.add(ins.getAddress() + "\t" + java.util.HexFormat.of().formatHex(ins.getBytes()) + "\t" + ins);
                }
                String assemblyStatus = instructions.hasNext() ? "truncated_at_" + instructionLimit : "complete";
                Files.write(output.resolve(stem + ".asm.txt"), assembly, StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW);
                DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
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
        println("WHT_QUTS_TRACE_OK functions=" + functions.size() + " seeds=" + seeds.size());
    }
}
