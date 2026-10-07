// Annotate the exact owned Qualcomm image; never attach to a device or process.
// Labels describe research roles, not recovered vendor symbols or a live API.
// @category WiFiHardwareTime

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.CategoryPath;
import ghidra.program.model.data.DataTypeConflictHandler;
import ghidra.program.model.data.DWordDataType;
import ghidra.program.model.data.StructureDataType;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class AnnotateQualcommTiming extends GhidraScript {
    private static final String SHA256 =
        "ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115";
    private record Target(long rva, String role, String note, boolean export) {}

    private static final Target[] TARGETS = {
        new Target(0x168ce0, "wmi_control_rx", "Dispatches decoded event; selected history path excludes management event 0x7001.", true),
        new Target(0x1ba4e0, "wmi_decode", "Generic event decoder; candidate fields require independent firmware semantics.", false),
        new Target(0x1a8160, "management_rx", "Copies frame, reduces metadata; candidate header +0x34/+0x38/+0x3c and optional timing slot are not forwarded by this selected handler.", true),
        new Target(0x1a6080, "management_metadata_reduce", "Compact metadata conversion; not a complete-event exporter.", true),
        new Target(0x104230, "management_enqueue", "Downstream management-frame enqueue; do not infer original header lifetime.", false),
        new Target(0x1bae60, "wmi_decoded_cleanup", "Post-callback cleanup; wrapper pointers are not owned application data.", false),
        new Target(0x216b00, "tsf_report", "Separate diagnostic TSF report path; not the management-frame producer.", false),
        new Target(0x1955e8, "tsf_command_builder", "Separate command construction; no fresh-sampling contract established.", false),
        new Target(0x25780, "bss_indication", "BSS list indication path; cache discovery time is not QPC correlation.", false),
        new Target(0x57830, "bss_entry_construct", "Constructs BSS export from cached data; local RX timing is not established here.", false),
        new Target(0x161a50, "bss_serialize", "BSS serializer; AP advertised timestamp and system discovery time remain different clocks.", false),
        new Target(0x12e4f0, "ihv_request", "Vendor request bridge, serialization and completion; internal selectors are not a supported public ABI.", true),
        new Target(0x11cde8, "nic_specific_dispatch", "Outer selector 0xff500001 starts logging; 0xff500002 selects combined read. Do not invoke from these annotations.", true),
        new Target(0x37e00, "packetlog_result_envelope", "12-byte prefix plus log output. External length/error and access contracts remain unqualified.", true),
        new Target(0xcdd8, "packetlog_combined_copy", "Header then body via operations slots +0x270/+0x278; not an atomic snapshot.", true),
        new Target(0xcfa0, "packetlog_header_wrapper", "Inner header route; outer dispatch can intercept the same selector and start logging.", false),
        new Target(0xcf58, "packetlog_body_wrapper", "Inner body route; selected combined path has a separate envelope.", false),
        new Target(0x18ae30, "packetlog_header_thunk", "Installed table slot +0x270 forwards to 0x1ebe50.", false),
        new Target(0x18ae40, "packetlog_body_thunk", "Installed table slot +0x278 forwards to 0x1ebdc0.", false),
        new Target(0x1ebe50, "packetlog_header_read", "Copies eight-byte prologue; not a complete record or snapshot guarantee.", true),
        new Target(0x1ebdc0, "packetlog_body_read", "Body reader; matching writer publication lock has not been established.", true),
        new Target(0x1ebbf8, "packetlog_copy", "Cursor/wrap-dependent copy; concurrent publication and teardown remain unresolved.", true),
        new Target(0x2171e0, "packetlog_context_lookup", "Global module 0x19 plus indirect selector-zero lookup; interface argument alone does not establish source identity.", true),
        new Target(0x197420, "global_module_lookup", "Module-context resolver used by packet-log lookup.", false),
        new Target(0x1ebb60, "packetlog_allocate", "Allocates capacity plus 0x14 bytes; storage lifetime is distinct from request lifetime.", false),
        new Target(0x220ac0, "packetlog_reserve_adapter", "Narrows input header +8 to 16 bits; field semantics remain unqualified.", true),
        new Target(0x220b18, "packetlog_reserve", "Advances write cursor before caller copies payload. Cursor progress is not a completed-record marker.", true),
        new Target(0x220e90, "packetlog_offload_write", "Reserves then copies input +0x10 payload; no binding to complete WMI management event established.", true),
        new Target(0x220f98, "packetlog_lite_write", "Packet-log payload copy; packet view is not necessarily an RX descriptor plus entire frame.", true),
        new Target(0x221320, "packetlog_rx_packet_write", "Copies packet data view using local log type 0x16; descriptor retention unproven.", false),
        new Target(0x221428, "packetlog_rx_info_write", "Checks logging-header length then copies opaque bytes; timestamp schema unproven.", true),
        new Target(0x1ec0e0, "packetlog_stop_reset", "Stop/reset can release storage; not a demonstrated freeze-and-read operation.", true),
        new Target(0x1ebee0, "packetlog_release", "Clears backing pointer and frees storage; lifetime pinning remains unqualified.", true),
        new Target(0x1619b0, "ihv_serialize", "Serializes returned bytes for vendor request completion.", false),
        new Target(0x13a890, "ihv_complete", "Copies serialized response into framework output subject to capacity checks.", true),
        new Target(0x1477f0, "ftm_event", "Separate FTM response path; aggregate ranging is not absolute event timestamp export.", false)
    };

    private static final Target[] SITES = {
        new Target(0x168e0c, "decode_call", "Raw event payload/length enter decoder.", false),
        new Target(0x168f88, "management_history_exclusion", "Selected history writer skips management event 0x7001; no substitute QPC sample.", false),
        new Target(0x169034, "event_callback", "Callback consumes borrowed decoded event; owned copy must preserve needed data before cleanup.", false),
        new Target(0x1690c8, "event_cleanup", "Cleanup after callback; copied wrapper pointers cannot extend data lifetime.", false),
        new Target(0x1bc6e4, "management_slot_cleanup", "Cleanup case tests allocation flags for twelve decoded slots.", false),
        new Target(0x341840, "packetlog_operations_table", "Selected installed table: +0x270 -> 0x18ae30; +0x278 -> 0x18ae40.", false),
        new Target(0x341c30, "module_global_pointer", "Global context pointer slot; runtime address/value is not known from file analysis.", false),
        new Target(0x220afc, "metadata_narrowing", "Reads 16-bit input metadata; do not label it a complete hardware timestamp.", false),
        new Target(0x220d84, "reservation_publish", "Write-position store occurs before callers copy payload.", false),
        new Target(0x220f80, "offload_payload_copy", "Payload copy follows reservation return.", false),
        new Target(0x2210d8, "lite_payload_copy", "Payload copy follows reservation return.", false),
        new Target(0x13a964, "application_output_copy", "Copy into framework response +0x10; does not certify source-buffer consistency.", false)
    };

    private Address at(long rva) { return currentProgram.getImageBase().add(rva); }

    private void annotate(Target target) throws Exception {
        Address address = at(target.rva());
        createBookmark(address, "WiFi timing research", target.role() + ": " + target.note());
        String note = "[WiFiHardwareTime exact-build static research] " + target.note();
        String previous = getPreComment(address);
        if (previous == null || !previous.contains(note)) {
            setPreComment(address, previous == null ? note : previous + "\n" + note);
        }
        createLabel(address, "wht_" + target.role(), false, SourceType.USER_DEFINED);
    }

    private void addReferenceTypes() {
        CategoryPath category = new CategoryPath("/WiFiHardwareTime/ReferenceOnly");
        StructureDataType header = new StructureDataType(category, "MgmtHeaderCandidates", 72);
        header.setDescription("REFERENCE HYPOTHESIS ONLY. Offsets match a public schema; live contents, clock identity, units and split-word correction are unqualified. Not applied to program variables.");
        header.replaceAtOffset(0x34, DWordDataType.dataType, 4, "candidate_tsf_delta", "Public-schema candidate; signedness and runtime semantics require qualification.");
        header.replaceAtOffset(0x38, DWordDataType.dataType, 4, "candidate_rx_tsf_low", "Public-schema low word; exact firmware sampling instant unqualified.");
        header.replaceAtOffset(0x3c, DWordDataType.dataType, 4, "candidate_rx_tsf_high", "May be sampled later; concatenation is not an atomic latch proof.");
        StructureDataType ring = new StructureDataType(category, "PacketLogBackingHeader", 20);
        ring.setDescription("Selected static layout only; no snapshot, publication or lifetime guarantee. Not applied to program variables.");
        ring.replaceAtOffset(8, DWordDataType.dataType, 4, "read_position", "Selected cursor interpretation.");
        ring.replaceAtOffset(12, DWordDataType.dataType, 4, "reservation_position", "Can advance before payload copy.");
        ring.replaceAtOffset(16, DWordDataType.dataType, 4, "wrap_position", "Selected wrap handling; not an epoch counter.");
        for (StructureDataType type : new StructureDataType[] { header, ring }) {
            currentProgram.getDataTypeManager().addDataType(type, DataTypeConflictHandler.KEEP_HANDLER);
        }
    }

    @Override
    public void run() throws Exception {
        if (currentProgram == null || !SHA256.equalsIgnoreCase(currentProgram.getExecutableSHA256())) {
            throw new IllegalArgumentException("Exact imported-file SHA-256 mismatch; annotations refused");
        }
        if (!"AARCH64:LE:64:v8A".equals(currentProgram.getLanguageID().toString()) ||
            !"windows".equals(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) ||
            currentProgram.getImageBase().getOffset() != 0x140000000L) {
            throw new IllegalArgumentException("Expected ARM64 Windows compiler spec and original image base");
        }
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("Pass one NEW private output directory under ignored artifacts");
        }
        Path output = Path.of(args[0]).toAbsolutePath();
        Files.createDirectory(output); // Refuse replacement of previous evidence.
        for (Target target : TARGETS) {
            monitor.checkCancelled();
            if (!currentProgram.getMemory().contains(at(target.rva()))) {
                throw new IllegalStateException("Target outside imported memory: " + target.role());
            }
        }
        List<String> receipt = new ArrayList<>();
        receipt.add("sha256\t" + SHA256);
        receipt.add("language\t" + currentProgram.getLanguageID());
        receipt.add("compiler\t" + currentProgram.getCompilerSpec().getCompilerSpecID());
        receipt.add("evidence\toffline decompilation; no device or firmware execution");
        receipt.add("rva\trole\tfunction_entry\tdecompilation");
        for (Target target : TARGETS) {
            annotate(target);
            Function function = getFunctionAt(at(target.rva()));
            if (function != null && function.getSymbol().getSource() == SourceType.DEFAULT) {
                function.setName("wht_" + target.role(), SourceType.USER_DEFINED);
            }
        }
        for (Target target : SITES) { annotate(target); }
        addReferenceTypes();
        DecompInterface decompiler = new DecompInterface();
        int failures = 0;
        try {
            if (!decompiler.openProgram(currentProgram)) {
                throw new IllegalStateException("Native decompiler failed: " + decompiler.getLastMessage());
            }
            for (Target target : TARGETS) {
                monitor.checkCancelled();
                Function function = getFunctionAt(at(target.rva()));
                String status = "not_requested";
                if (function == null) {
                    status = "missing_function_boundary";
                    failures++;
                } else if (target.export()) {
                    DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
                    if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                        Files.writeString(output.resolve(target.role() + ".c.txt"),
                            "/* Offline decompiler hypothesis; check instructions. Not vendor source. */\n" +
                            result.getDecompiledFunction().getC(), StandardCharsets.UTF_8,
                            StandardOpenOption.CREATE_NEW);
                        status = "completed";
                    } else {
                        status = "failed:" + result.getErrorMessage().replace('\n', ' ').replace('\r', ' ');
                        failures++;
                    }
                }
                receipt.add(String.format("0x%x\t%s\t%s\t%s", target.rva(), target.role(),
                    function == null ? "missing" : function.getEntryPoint(), status));
            }
        } finally { decompiler.dispose(); }
        receipt.add("bookmarked_locations\t" + (TARGETS.length + SITES.length));
        receipt.add("failures\t" + failures);
        Files.write(output.resolve("receipt.tsv"), receipt, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW);
        if (failures != 0) {
            throw new IllegalStateException("Incomplete analysis: inspect private receipt; failures=" + failures);
        }
        println("WHT_ANNOTATION_OK functions=" + TARGETS.length + " sites=" + SITES.length +
            " private_reports=" + output);
    }
}
