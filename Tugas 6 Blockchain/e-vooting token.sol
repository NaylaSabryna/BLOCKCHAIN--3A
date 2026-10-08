// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Import ERC721 dan ERC721URIStorage dari OpenZeppelin sesuai Modul 6
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";

/**
 * @title Sistem EVotingBlockchain dengan Tokenisasi (ERC-721)
 * @dev Konversi dari skrip Python E-Voting Jaringan Tertutup & Integrasi Standar Token ERC-721 Modul 6
 */
contract EVotingBlockchain is ERC721URIStorage {
    
    // -------------------------------------------------------------
    // 1. ENUM & STRUCT (Tipe Data Kustom)
    // -------------------------------------------------------------
    
    enum VoteStatus {
        CREATED,        // 0: Kotak suara TPS dibuka
        VOTED,          // 1: Pemilih telah memberikan suara
        VERIFIED_LOCAL, // 2: Suara divalidasi oleh Otoritas TPS
        IN_RECAP,       // 3: Dalam proses rekapitulasi bertingkat
        FINAL_COUNT,    // 4: Masuk ke penghitungan akhir
        FINISHED        // 5: Proses selesai & sah
    }

    struct BlockData {
        uint256 tokenId;        // ID Token NFT terkait batch suara
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
    // 2. STATE VARIABLES & MAPPINGS
    // -------------------------------------------------------------
    
    address public contractOwner;
    uint256 private nextTokenId = 1; // Counter Auto-Increment Token ID NFT
    
    // Array blockchain menampung seluruh blok suara
    BlockData[] public blockchain;
    
    // Mapping Token ID ke Data Block
    mapping(uint256 => BlockData) public batchTokens;

    // Mapping riwayat event per blok berdasarkan ID Batch
    mapping(string => HistoryRecord[]) private historyLogs;

    // -------------------------------------------------------------
    // 3. CUSTOM ERRORS
    // -------------------------------------------------------------
    error HanyaPanitia();
    error BlockchainKosong();
    error VerifikasiGagal(bytes32 calculatedHash, bytes32 storedHash);

    // -------------------------------------------------------------
    // 4. EVENTS
    // -------------------------------------------------------------
    event VoteBatchCreated(uint256 indexed tokenId, string indexed batchId, string tpsLocation, address indexed owner);
    event StatusUpdated(string indexed batchId, VoteStatus status, address indexed actor);
    event LocalVerified(uint256 indexed blockIndex, bytes32 blockHash, bool isValid);

    // -------------------------------------------------------------
    // 5. MODIFIERS
    // -------------------------------------------------------------
    modifier onlyPanitia() {
        if (msg.sender != contractOwner) revert HanyaPanitia();
        _;
    }

    // -------------------------------------------------------------
    // 6. CONSTRUCTOR
    // -------------------------------------------------------------
    // Menginisialisasi Nama Token dan Simbol NFT E-Voting
    constructor() ERC721("EVotingBatchToken", "EVOTE") {
        contractOwner = msg.sender;
    }

    // -------------------------------------------------------------
    // 7. INTERNAL FUNCTIONS (MINT TOKEN)
    // -------------------------------------------------------------
    /**
     * @notice Fungsi internal untuk melakukan Mint NFT Batch Suara
     */
    function _mintBatchNFT(address to, string memory metadataURI) internal returns (uint256) {
        uint256 tokenId = nextTokenId;
        nextTokenId++;

        _safeMint(to, tokenId);
        _setTokenURI(tokenId, metadataURI);

        return tokenId;
    }

    // -------------------------------------------------------------
    // 8. MAIN FUNCTIONS
    // -------------------------------------------------------------

    /**
     * @notice [PROSES 1] Buat Batch Suara & Mint NFT Suara TPS
     */
    function buatBatchSuara(
        string memory _batchId,
        string memory _tpsLocation,
        uint256 _totalVoters,
        string memory _voterId,
        string memory _candidateChoice,
        string memory _metadataURI
    ) external onlyPanitia returns (uint256) {
        
        // 1. Generate Token ID & Mint NFT
        uint256 tokenId = _mintBatchNFT(msg.sender, _metadataURI);

        // 2. Hitung Hash Block
        uint256 blockIndex = blockchain.length + 1;
        bytes32 prevHash = blockIndex == 1 ? bytes32(0) : blockchain[blockchain.length - 1].blockHash;

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

        // 3. Buat Struct BlockData Baru
        BlockData memory newBlock = BlockData({
            tokenId: tokenId,
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

        // 4. Simpan ke Array & Mapping
        blockchain.push(newBlock);
        batchTokens[tokenId] = newBlock;

        // 5. Tambah Riwayat History
        _addHistory(
            _batchId, 
            "VOTE_BATCH_CREATED", 
            string(abi.encodePacked("Kotak suara ", _batchId, " dibuka di ", _tpsLocation, " (NFT ID: ", _toString(tokenId), ")"))
        );

        emit VoteBatchCreated(tokenId, _batchId, _tpsLocation, msg.sender);

        return tokenId;
    }

    /**
     * @notice [PROSES 2] Verifikasi Lokal (Integritas Blok)
     */
    function verifikasiLokal() external returns (bool) {
        if (blockchain.length == 0) revert BlockchainKosong();

        uint256 lastIdx = blockchain.length - 1;
        BlockData storage targetBlock = blockchain[lastIdx];

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

        targetBlock.status = VoteStatus.VERIFIED_LOCAL;
        batchTokens[targetBlock.tokenId].status = VoteStatus.VERIFIED_LOCAL;
        
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
        batchTokens[targetBlock.tokenId].status = VoteStatus.IN_RECAP;
        
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

        targetBlock.status = VoteStatus.FINAL_COUNT;
        batchTokens[targetBlock.tokenId].status = VoteStatus.FINAL_COUNT;
        emit StatusUpdated(targetBlock.batchId, VoteStatus.FINAL_COUNT, msg.sender);

        targetBlock.status = VoteStatus.FINISHED;
        batchTokens[targetBlock.tokenId].status = VoteStatus.FINISHED;
        _addHistory(targetBlock.batchId, "FINISHED", "Seluruh blok aman & penghitungan sah selesai");
        emit StatusUpdated(targetBlock.batchId, VoteStatus.FINISHED, msg.sender);
    }

    // -------------------------------------------------------------
    // 9. HELPER & TOKEN QUERY FUNCTIONS
    // -------------------------------------------------------------
    
    /**
     * @notice Mengecek pemilik NFT berdasarkan Token ID (Sesuai Modul 6)
     */
    function getBatchOwner(uint256 _tokenId) external view returns (address) {
        require(ownerOf(_tokenId) != address(0), "NFT Token ID tidak ditemukan");
        return ownerOf(_tokenId);
    }

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

    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}