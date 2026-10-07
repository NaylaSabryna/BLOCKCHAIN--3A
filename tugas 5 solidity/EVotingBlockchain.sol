// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Sistem EVotingBlockchain
 * @dev Konversi dari skrip Python E-Voting Jaringan Tertutup sesuai Modul 5 Smart Contract II
 */
contract EVotingBlockchain {
    
    // -------------------------------------------------------------
    // 1. ENUM & STRUCT (Tipe Data Kustom Sesuai Modul 5)
    // -------------------------------------------------------------
    
    // Sama seperti vote_status.py
    enum VoteStatus {
        CREATED,        // 0: Kotak suara TPS dibuka
        VOTED,          // 1: Pemilih telah memberikan suara
        VERIFIED_LOCAL, // 2: Suara divalidasi oleh Otoritas TPS (Jaringan Tertutup)
        IN_RECAP,       // 3: Dalam proses rekapitulasi bertingkat
        FINAL_COUNT,    // 4: Masuk ke penghitungan akhir
        FINISHED        // 5: Proses selesai & sah
    }

    // Identik dengan properti Block di block.py & VoteBatch di vote_batch.py
    struct BlockData {
        uint256 index;
        uint256 timestamp;
        string batchId;
        string tpsLocation;
        uint256 totalVoters;
        string voterId;
        string candidateChoice;
        address owner;
        bytes32 previousHash;
        bytes32 blockHash;
        VoteStatus status;
    }

    struct HistoryRecord {
        uint256 timestamp;
        string eventType;
        address owner;
        VoteStatus status;
        string details;
    }

    // -------------------------------------------------------------
    // 2. STATE VARIABLES & MAPPINGS (Penyimpanan Data On-Chain)
    // -------------------------------------------------------------
    
    address public owner;
    
    // Array blockchain menampung seluruh blok suara (Sesuai materi Arrays di Modul 5)
    BlockData[] public blockchain;
    
    // Mapping riwayat event per blok berdasarkan ID Batch (Sesuai materi Mappings di Modul 5)
    mapping(string => HistoryRecord[]) private historyLogs;

    // -------------------------------------------------------------
    // 3. CUSTOM ERRORS (Efisiensi Biaya Gas - Sesuai Modul 5)
    // -------------------------------------------------------------
    error HanyaPanitia();
    error BlockchainKosong();
    error VerifikasiGagal(bytes32 calculatedHash, bytes32 storedHash);

    // -------------------------------------------------------------
    // 4. EVENTS (Logika Logging Off-Chain - Sesuai Modul 5)
    // -------------------------------------------------------------
    event VoteBatchCreated(string indexed batchId, string tpsLocation, address indexed owner);
    event StatusUpdated(string indexed batchId, VoteStatus status, address indexed actor);
    event LocalVerified(uint256 indexed blockIndex, bytes32 blockHash, bool isValid);

    // -------------------------------------------------------------
    // 5. MODIFIERS (Akses Kontrol)
    // -------------------------------------------------------------
    modifier onlyPanitia() {
        if (msg.sender != owner) revert HanyaPanitia();
        _;
    }

    // -------------------------------------------------------------
    // 6. CONSTRUCTOR
    // -------------------------------------------------------------
    constructor() {
        owner = msg.sender;
    }

    // -------------------------------------------------------------
    // 7. MAIN FUNCTIONS (Menu 1 - 4 pada main.py)
    // -------------------------------------------------------------

    /**
     * @notice [PROSES 1] Buat Batch Suara (Inisialisasi TPS)
     * @dev Menggantikan class VoteBatch & penambahan ke blockchain
     */
    function buatBatchSuara(
        string memory _batchId,
        string memory _tpsLocation,
        uint256 _totalVoters,
        string memory _voterId,
        string memory _candidateChoice
    ) external onlyPanitia {
        
        uint256 blockIndex = blockchain.length + 1;
        bytes32 prevHash = blockIndex == 1 ? bytes32(0) : blockchain[blockchain.length - 1].blockHash;

        // Hitung SHA-256 Hash blok (Sesuai calculate_hash di block.py)
        bytes32 newHash = keccak256(
            abi.encodePacked(
                blockIndex,
                block.timestamp,
                _batchId,
                _voterId,
                _candidateChoice,
                _tpsLocation,
                prevHash
            )
        );

        // Buat Blok baru
        BlockData memory newBlock = BlockData({
            index: blockIndex,
            timestamp: block.timestamp,
            batchId: _batchId,
            tpsLocation: _tpsLocation,
            totalVoters: _totalVoters,
            voterId: _voterId,
            candidateChoice: _candidateChoice,
            owner: msg.sender,
            previousHash: prevHash,
            blockHash: newHash,
            status: VoteStatus.CREATED
        });

        blockchain.push(newBlock);

        // Tambah riwayat event ke mapping
        _addHistory(
            _batchId, 
            "VOTE_BATCH_CREATED", 
            string(abi.encodePacked("Kotak suara ", _batchId, " dibuka di ", _tpsLocation))
        );

        emit VoteBatchCreated(_batchId, _tpsLocation, msg.sender);
    }

    /**
     * @notice [PROSES 2] Verifikasi Lokal (Integritas Blok)
     * @dev Menggantikan fungsi verify_local_block di local_validator.py
     */
    function verifikasiLokal() external returns (bool) {
        if (blockchain.length == 0) revert BlockchainKosong();

        uint256 lastIdx = blockchain.length - 1;
        BlockData storage targetBlock = blockchain[lastIdx];

        // Rekalkulasi Hash untuk mengecek Integritas Data
        bytes32 calculatedHash = keccak256(
            abi.encodePacked(
                targetBlock.index,
                targetBlock.timestamp,
                targetBlock.batchId,
                targetBlock.voterId,
                targetBlock.candidateChoice,
                targetBlock.tpsLocation,
                targetBlock.previousHash
            )
        );

        if (targetBlock.blockHash != calculatedHash) {
            emit LocalVerified(targetBlock.index, calculatedHash, false);
            revert VerifikasiGagal(calculatedHash, targetBlock.blockHash);
        }

        // Perbarui Status ke VERIFIED_LOCAL
        targetBlock.status = VoteStatus.VERIFIED_LOCAL;
        
        _addHistory(targetBlock.batchId, "VERIFIED_LOCAL", "Integritas blok suara terverifikasi sah");
        emit StatusUpdated(targetBlock.batchId, VoteStatus.VERIFIED_LOCAL, msg.sender);
        emit LocalVerified(targetBlock.index, targetBlock.blockHash, true);

        return true;
    }

    /**
     * @notice [PROSES 3] Rekapitulasi Bertingkat
     */
    function rekapitulasiBertingkat() external onlyPanitia {
        if (blockchain.length == 0) revert BlockchainKosong();

        uint256 lastIdx = blockchain.length - 1;
        BlockData storage targetBlock = blockchain[lastIdx];

        targetBlock.status = VoteStatus.IN_RECAP;
        
        _addHistory(targetBlock.batchId, "IN_RECAP", "Blok dimasukkan ke rantai rekapitulasi bertingkat");
        emit StatusUpdated(targetBlock.batchId, VoteStatus.IN_RECAP, msg.sender);
    }

    /**
     * @notice [PROSES 4] Penghitungan & Verifikasi Akhir
     */
    function penghitunganAkhir() external onlyPanitia {
        if (blockchain.length == 0) revert BlockchainKosong();

        uint256 lastIdx = blockchain.length - 1;
        BlockData storage targetBlock = blockchain[lastIdx];

        // Transisi Status 1: FINAL_COUNT
        targetBlock.status = VoteStatus.FINAL_COUNT;
        emit StatusUpdated(targetBlock.batchId, VoteStatus.FINAL_COUNT, msg.sender);

        // Transisi Status 2: FINISHED
        targetBlock.status = VoteStatus.FINISHED;
        _addHistory(targetBlock.batchId, "FINISHED", "Seluruh blok aman & penghitungan sah selesai");
        emit StatusUpdated(targetBlock.batchId, VoteStatus.FINISHED, msg.sender);
    }

    // -------------------------------------------------------------
    // 8. HELPER / READ-ONLY FUNCTIONS (Sesuai Materi Modul 5)
    // -------------------------------------------------------------
    
    function _addHistory(string memory _batchId, string memory _eventType, string memory _details) internal {
        uint256 lastIdx = blockchain.length - 1;
        historyLogs[_batchId].push(HistoryRecord({
            timestamp: block.timestamp,
            eventType: _eventType,
            owner: msg.sender,
            status: blockchain[lastIdx].status,
            details: _details
        }));
    }

    function getBlockchainLength() external view returns (uint256) {
        return blockchain.length;
    }

    function getHistory(string memory _batchId) external view returns (HistoryRecord[] memory) {
        return historyLogs[_batchId];
    }
}