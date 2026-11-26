// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * EVOTE - Decentralized Electronic Voting System (MODE PROTOTIPE TRANSPARAN)
 *
 * Catatan privasi: pemanggilan vote(electionId, candidateId) bersifat publik di blockchain.
 * Kontrak ini TIDAK menyimpan pemetaan wallet -> kandidat dan TIDAK memancarkan kandidat
 * pada event, tetapi calldata transaksi tetap dapat dibaca publik. Ini bukan secret ballot.
 * Data identitas (NIK/NIM/Custom ID) tidak pernah masuk ke kontrak; hanya hash bergaram.
 */
contract EVotingBlockchain is AccessControl {
    bytes32 public constant PANITIA_ROLE = keccak256("PANITIA_ROLE");

    // ---------------------------------------------------------------- Periode
    enum ElectionState { DRAFT, PUBLISHED, CANCELLED, FINALIZED }

    struct Election {
        uint256 id;
        string name;
        uint64 startTime;
        uint64 endTime;
        bytes32 metadataHash;
        ElectionState state;
        uint256 candidateCount;   // jumlah id kandidat yang pernah dibuat
        uint256 activeCandidates; // kandidat aktif saat ini
        uint256 totalVotes;
        uint256 approvedVoters;
        uint64 createdAt;
    }

    struct Candidate {
        uint256 id;
        uint256 nomorUrut;
        string name;
        bytes32 metadataHash;
        bool active;
    }

    uint256 public electionCount;
    mapping(uint256 => Election) private elections;
    mapping(uint256 => mapping(uint256 => Candidate)) private candidates;
    mapping(uint256 => mapping(uint256 => bool)) private nomorUrutUsed;
    mapping(uint256 => mapping(uint256 => uint256)) private tally;
    mapping(uint256 => mapping(address => bool)) private eligible;
    mapping(uint256 => mapping(address => bool)) private voted;
    mapping(uint256 => mapping(bytes32 => bool)) private credentialUsed;

    // ------------------------------------------------- Audit checkpoint (lama)
    enum VoteStatus { CREATED, VERIFIED_LOCAL, IN_RECAP, FINAL_COUNT, FINISHED }

    struct BlockData {
        uint256 index;
        uint256 timestamp;
        uint256 electionId;
        string batchId;
        string catatan;
        uint256 totalVotes;
        bytes32 snapshotHash;
        bytes32 previousHash;
        bytes32 blockHash;
        address actor;
        VoteStatus status;
    }

    struct HistoryRecord {
        uint256 timestamp;
        string eventType;
        address actor;
        VoteStatus status;
        string details;
    }

    BlockData[] private blockchain;
    mapping(string => uint256) private batchIndexPlusOne;
    mapping(string => HistoryRecord[]) private historyLogs;

    // ------------------------------------------------------------------ Error
    error ElectionNotFound();
    error CandidateNotFound();
    error InvalidTimeRange();
    error StartMustBeInFuture();
    error ElectionAlreadyStarted();
    error InvalidState();
    error NeedTwoCandidates();
    error DuplicateNomorUrut();
    error EmptyName();
    error InvalidAddress();
    error VoterNotEligible();
    error AlreadyVoted();
    error VotingNotOpen();
    error CredentialAlreadyUsed();
    error AlreadyApproved();
    error ElectionNotEnded();
    error ElectionNotFinalized();
    error BatchIdExists();
    error BatchNotFound();
    error EmptyBatchId();
    error InvalidTransition();
    error NoCheckpoints();

    // ------------------------------------------------------------------ Event
    event ElectionCreated(uint256 indexed electionId, string name, uint64 startTime, uint64 endTime, address indexed actor);
    event ElectionUpdated(uint256 indexed electionId, string name, uint64 startTime, uint64 endTime, address indexed actor);
    event ElectionPublished(uint256 indexed electionId, address indexed actor);
    event ElectionCancelled(uint256 indexed electionId, address indexed actor);
    event ElectionFinalized(uint256 indexed electionId, uint256 totalVotes, bytes32 resultHash, address indexed actor);
    event CandidateAdded(uint256 indexed electionId, uint256 indexed candidateId, uint256 nomorUrut, string name, address indexed actor);
    event CandidateUpdated(uint256 indexed electionId, uint256 indexed candidateId, uint256 nomorUrut, string name, address indexed actor);
    event CandidateRemoved(uint256 indexed electionId, uint256 indexed candidateId, address indexed actor);
    event VoterApproved(uint256 indexed electionId, address indexed voter, bytes32 credentialHash, address indexed actor);
    event VoteCast(uint256 indexed electionId, address indexed voter);
    event CheckpointCreated(uint256 indexed electionId, uint256 indexed index, string batchId, bytes32 blockHash, address indexed actor);
    event StatusUpdated(string batchId, VoteStatus status, address indexed actor);
    event LocalVerified(uint256 indexed blockIndex, bytes32 blockHash, bool isValid);

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PANITIA_ROLE, msg.sender);
    }

    // ------------------------------------------------------------- Modifiers
    modifier electionExists(uint256 eid) {
        if (eid == 0 || eid > electionCount) revert ElectionNotFound();
        _;
    }

    modifier beforeStart(uint256 eid) {
        Election storage e = elections[eid];
        if (e.state != ElectionState.DRAFT && e.state != ElectionState.PUBLISHED) revert InvalidState();
        if (block.timestamp >= e.startTime) revert ElectionAlreadyStarted();
        _;
    }

    // ------------------------------------------------------ Manajemen periode
    function createElection(string calldata name, uint64 startTime, uint64 endTime, bytes32 metadataHash)
        external onlyRole(PANITIA_ROLE) returns (uint256)
    {
        if (bytes(name).length == 0) revert EmptyName();
        if (endTime <= startTime) revert InvalidTimeRange();
        if (startTime <= block.timestamp) revert StartMustBeInFuture();
        uint256 eid = ++electionCount;
        Election storage e = elections[eid];
        e.id = eid;
        e.name = name;
        e.startTime = startTime;
        e.endTime = endTime;
        e.metadataHash = metadataHash;
        e.state = ElectionState.DRAFT;
        e.createdAt = uint64(block.timestamp);
        emit ElectionCreated(eid, name, startTime, endTime, msg.sender);
        return eid;
    }

    function updateElection(uint256 eid, string calldata name, uint64 startTime, uint64 endTime, bytes32 metadataHash)
        external onlyRole(PANITIA_ROLE) electionExists(eid) beforeStart(eid)
    {
        if (bytes(name).length == 0) revert EmptyName();
        if (endTime <= startTime) revert InvalidTimeRange();
        if (startTime <= block.timestamp) revert StartMustBeInFuture();
        Election storage e = elections[eid];
        e.name = name;
        e.startTime = startTime;
        e.endTime = endTime;
        e.metadataHash = metadataHash;
        emit ElectionUpdated(eid, name, startTime, endTime, msg.sender);
    }

    function publishElection(uint256 eid) external onlyRole(PANITIA_ROLE) electionExists(eid) beforeStart(eid) {
        Election storage e = elections[eid];
        if (e.state != ElectionState.DRAFT) revert InvalidState();
        if (e.activeCandidates < 2) revert NeedTwoCandidates();
        e.state = ElectionState.PUBLISHED;
        emit ElectionPublished(eid, msg.sender);
    }

    function cancelElection(uint256 eid) external onlyRole(PANITIA_ROLE) electionExists(eid) {
        Election storage e = elections[eid];
        if (e.state != ElectionState.DRAFT && e.state != ElectionState.PUBLISHED) revert InvalidState();
        if (block.timestamp > e.endTime) revert InvalidState();
        e.state = ElectionState.CANCELLED;
        emit ElectionCancelled(eid, msg.sender);
    }

    /// Finalisasi hanya setelah waktu berakhir. Membuat checkpoint audit otomatis.
    function finalizeElection(uint256 eid) external onlyRole(PANITIA_ROLE) electionExists(eid) {
        Election storage e = elections[eid];
        if (e.state != ElectionState.PUBLISHED) revert InvalidState();
        if (block.timestamp <= e.endTime) revert ElectionNotEnded();
        e.state = ElectionState.FINALIZED;
        bytes32 snap = _snapshotHash(eid);
        emit ElectionFinalized(eid, e.totalVotes, snap, msg.sender);
        _appendCheckpoint(eid, string.concat("FINAL-", _toString(eid)), "Finalisasi hasil periode pemilihan", VoteStatus.CREATED, "FINALIZED");
    }

    // ------------------------------------------------------ Manajemen kandidat
    function addCandidate(uint256 eid, uint256 nomorUrut, string calldata name, bytes32 metadataHash)
        external onlyRole(PANITIA_ROLE) electionExists(eid) beforeStart(eid) returns (uint256)
    {
        if (bytes(name).length == 0) revert EmptyName();
        if (nomorUrut == 0 || nomorUrutUsed[eid][nomorUrut]) revert DuplicateNomorUrut();
        Election storage e = elections[eid];
        uint256 cid = ++e.candidateCount;
        e.activeCandidates++;
        nomorUrutUsed[eid][nomorUrut] = true;
        candidates[eid][cid] = Candidate(cid, nomorUrut, name, metadataHash, true);
        emit CandidateAdded(eid, cid, nomorUrut, name, msg.sender);
        return cid;
    }

    function updateCandidate(uint256 eid, uint256 cid, uint256 nomorUrut, string calldata name, bytes32 metadataHash)
        external onlyRole(PANITIA_ROLE) electionExists(eid) beforeStart(eid)
    {
        Candidate storage c = candidates[eid][cid];
        if (cid == 0 || !c.active) revert CandidateNotFound();
        if (bytes(name).length == 0) revert EmptyName();
        if (nomorUrut == 0) revert DuplicateNomorUrut();
        if (nomorUrut != c.nomorUrut) {
            if (nomorUrutUsed[eid][nomorUrut]) revert DuplicateNomorUrut();
            nomorUrutUsed[eid][c.nomorUrut] = false;
            nomorUrutUsed[eid][nomorUrut] = true;
            c.nomorUrut = nomorUrut;
        }
        c.name = name;
        c.metadataHash = metadataHash;
        emit CandidateUpdated(eid, cid, nomorUrut, name, msg.sender);
    }

    function removeCandidate(uint256 eid, uint256 cid)
        external onlyRole(PANITIA_ROLE) electionExists(eid) beforeStart(eid)
    {
        Candidate storage c = candidates[eid][cid];
        if (cid == 0 || !c.active) revert CandidateNotFound();
        Election storage e = elections[eid];
        if (e.state == ElectionState.PUBLISHED && e.activeCandidates <= 2) revert NeedTwoCandidates();
        c.active = false;
        nomorUrutUsed[eid][c.nomorUrut] = false;
        e.activeCandidates--;
        emit CandidateRemoved(eid, cid, msg.sender);
    }

    // --------------------------------------------------------- Hak memilih
    function approveVoter(uint256 eid, address voter, bytes32 credentialHash)
        external onlyRole(PANITIA_ROLE) electionExists(eid)
    {
        Election storage e = elections[eid];
        if (e.state != ElectionState.DRAFT && e.state != ElectionState.PUBLISHED) revert InvalidState();
        if (block.timestamp > e.endTime) revert InvalidState();
        if (voter == address(0)) revert InvalidAddress();
        if (eligible[eid][voter]) revert AlreadyApproved();
        if (credentialUsed[eid][credentialHash]) revert CredentialAlreadyUsed();
        eligible[eid][voter] = true;
        credentialUsed[eid][credentialHash] = true;
        e.approvedVoters++;
        emit VoterApproved(eid, voter, credentialHash, msg.sender);
    }

    // ------------------------------------------------------------- Voting
    function vote(uint256 eid, uint256 cid) external electionExists(eid) {
        Election storage e = elections[eid];
        if (e.state != ElectionState.PUBLISHED || block.timestamp < e.startTime || block.timestamp > e.endTime) {
            revert VotingNotOpen();
        }
        if (!eligible[eid][msg.sender]) revert VoterNotEligible();
        if (voted[eid][msg.sender]) revert AlreadyVoted();
        Candidate storage c = candidates[eid][cid];
        if (cid == 0 || !c.active) revert CandidateNotFound();
        voted[eid][msg.sender] = true; // effects sebelum interaksi (tidak ada panggilan eksternal)
        tally[eid][cid] += 1;
        e.totalVotes += 1;
        emit VoteCast(eid, msg.sender);
    }

    // ------------------------------------------------------------- Pembacaan
    function getElection(uint256 eid) external view electionExists(eid) returns (Election memory) {
        return elections[eid];
    }

    function getCandidate(uint256 eid, uint256 cid) external view electionExists(eid) returns (Candidate memory) {
        if (cid == 0 || cid > elections[eid].candidateCount) revert CandidateNotFound();
        return candidates[eid][cid];
    }

    /// Mengembalikan semua kandidat (termasuk non-aktif) beserta perolehan suara.
    function getResults(uint256 eid)
        external view electionExists(eid)
        returns (uint256[] memory ids, uint256[] memory nomor, bool[] memory active, uint256[] memory votes)
    {
        uint256 n = elections[eid].candidateCount;
        ids = new uint256[](n);
        nomor = new uint256[](n);
        active = new bool[](n);
        votes = new uint256[](n);
        for (uint256 i = 1; i <= n; i++) {
            Candidate storage c = candidates[eid][i];
            ids[i - 1] = i;
            nomor[i - 1] = c.nomorUrut;
            active[i - 1] = c.active;
            votes[i - 1] = tally[eid][i];
        }
    }

    function isEligible(uint256 eid, address voter) external view returns (bool) { return eligible[eid][voter]; }
    function hasVoted(uint256 eid, address voter) external view returns (bool) { return voted[eid][voter]; }
    function isPanitia(address a) external view returns (bool) { return hasRole(PANITIA_ROLE, a); }

    function snapshotHash(uint256 eid) external view electionExists(eid) returns (bytes32) {
        return _snapshotHash(eid);
    }

    // -------------------------------------------------------- Audit checkpoint
    /// Membuat checkpoint integritas (rantai hash) dari kondisi suara periode saat ini.
    function buatBatchSuara(uint256 eid, string calldata batchId, string calldata catatan)
        external onlyRole(PANITIA_ROLE) electionExists(eid) returns (uint256)
    {
        if (bytes(batchId).length == 0) revert EmptyBatchId();
        if (_hasFinalPrefix(bytes(batchId))) revert BatchIdExists(); // awalan FINAL- dicadangkan untuk finalisasi
        if (elections[eid].state == ElectionState.CANCELLED || elections[eid].state == ElectionState.DRAFT) revert InvalidState();
        return _appendCheckpoint(eid, batchId, catatan, VoteStatus.CREATED, "VOTE_BATCH_CREATED");
    }

    /// Memeriksa ulang hash blok (bukan hanya blok terakhir) dan menandai VERIFIED_LOCAL bila sah.
    /// Kegagalan dicatat melalui event dan nilai false (tanpa revert) agar log tidak dibatalkan.
    function verifikasiLokal(uint256 index) external onlyRole(PANITIA_ROLE) returns (bool) {
        if (blockchain.length == 0) revert NoCheckpoints();
        if (index == 0 || index > blockchain.length) revert BatchNotFound();
        BlockData storage b = blockchain[index - 1];
        bool ok = _computeBlockHash(b) == b.blockHash
            && (index == 1 ? b.previousHash == bytes32(0) : b.previousHash == blockchain[index - 2].blockHash);
        emit LocalVerified(index, b.blockHash, ok);
        if (!ok) {
            _addHistory(b.batchId, "VERIFIKASI_GAGAL", "Hash blok tidak cocok", b.status);
            return false;
        }
        if (b.status == VoteStatus.CREATED) {
            b.status = VoteStatus.VERIFIED_LOCAL;
            emit StatusUpdated(b.batchId, b.status, msg.sender);
        }
        _addHistory(b.batchId, "VERIFIED_LOCAL", "Integritas blok terverifikasi sah", b.status);
        return true;
    }

    function rekapitulasiBertingkat(uint256 index) external onlyRole(PANITIA_ROLE) {
        BlockData storage b = _getBlockStorage(index);
        if (b.status != VoteStatus.VERIFIED_LOCAL) revert InvalidTransition();
        b.status = VoteStatus.IN_RECAP;
        _addHistory(b.batchId, "IN_RECAP", "Blok dimasukkan ke rekapitulasi bertingkat", b.status);
        emit StatusUpdated(b.batchId, b.status, msg.sender);
    }

    function penghitunganAkhir(uint256 index) external onlyRole(PANITIA_ROLE) {
        BlockData storage b = _getBlockStorage(index);
        if (b.status != VoteStatus.IN_RECAP) revert InvalidTransition();
        if (elections[b.electionId].state != ElectionState.FINALIZED) revert ElectionNotFinalized();
        b.status = VoteStatus.FINAL_COUNT;
        emit StatusUpdated(b.batchId, b.status, msg.sender);
        b.status = VoteStatus.FINISHED;
        _addHistory(b.batchId, "FINISHED", "Penghitungan akhir selesai", b.status);
        emit StatusUpdated(b.batchId, b.status, msg.sender);
    }

    function getBlockchainLength() external view returns (uint256) { return blockchain.length; }

    function getBlock(uint256 index) external view returns (BlockData memory) {
        if (index == 0 || index > blockchain.length) revert BatchNotFound();
        return blockchain[index - 1];
    }

    function getBlockIndexByBatchId(string calldata batchId) external view returns (uint256) {
        return batchIndexPlusOne[batchId];
    }

    function getHistory(string calldata batchId) external view returns (HistoryRecord[] memory) {
        return historyLogs[batchId];
    }

    /// Memeriksa seluruh rantai hash checkpoint. Mengembalikan (valid, indeks pertama yang rusak).
    function cekIntegritasRantai() external view returns (bool valid, uint256 firstInvalid) {
        bytes32 prev = bytes32(0);
        for (uint256 i = 0; i < blockchain.length; i++) {
            BlockData storage b = blockchain[i];
            if (b.previousHash != prev || _computeBlockHash(b) != b.blockHash) return (false, i + 1);
            prev = b.blockHash;
        }
        return (true, 0);
    }

    // ------------------------------------------------------------ Internal
    function _getBlockStorage(uint256 index) internal view returns (BlockData storage) {
        if (index == 0 || index > blockchain.length) revert BatchNotFound();
        return blockchain[index - 1];
    }

    function _appendCheckpoint(
        uint256 eid, string memory batchId, string memory catatan, VoteStatus st, string memory eventType
    ) internal returns (uint256) {
        if (batchIndexPlusOne[batchId] != 0) revert BatchIdExists();
        uint256 idx = blockchain.length + 1;
        bytes32 prev = idx == 1 ? bytes32(0) : blockchain[idx - 2].blockHash;
        BlockData memory b = BlockData({
            index: idx,
            timestamp: block.timestamp,
            electionId: eid,
            batchId: batchId,
            catatan: catatan,
            totalVotes: elections[eid].totalVotes,
            snapshotHash: _snapshotHash(eid),
            previousHash: prev,
            blockHash: bytes32(0),
            actor: msg.sender,
            status: st
        });
        b.blockHash = _computeBlockHash(b);
        blockchain.push(b);
        batchIndexPlusOne[batchId] = idx;
        _addHistory(batchId, eventType, catatan, st);
        emit CheckpointCreated(eid, idx, batchId, b.blockHash, msg.sender);
        return idx;
    }

    // abi.encode (bukan encodePacked) untuk menghindari ambiguitas hash antar string.
    function _computeBlockHash(BlockData memory b) internal pure returns (bytes32) {
        return keccak256(abi.encode(b.index, b.timestamp, b.electionId, b.batchId, b.totalVotes, b.snapshotHash, b.previousHash));
    }

    function _snapshotHash(uint256 eid) internal view returns (bytes32) {
        uint256 n = elections[eid].candidateCount;
        uint256[] memory votes = new uint256[](n);
        for (uint256 i = 1; i <= n; i++) votes[i - 1] = tally[eid][i];
        return keccak256(abi.encode(eid, elections[eid].totalVotes, votes));
    }

    function _addHistory(string memory batchId, string memory eventType, string memory details, VoteStatus st) internal {
        historyLogs[batchId].push(HistoryRecord(block.timestamp, eventType, msg.sender, st, details));
    }

    function _hasFinalPrefix(bytes memory b) internal pure returns (bool) {
        bytes memory p = bytes("FINAL-");
        if (b.length < p.length) return false;
        for (uint256 i = 0; i < p.length; i++) { if (b[i] != p[i]) return false; }
        return true;
    }

    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) { digits++; temp /= 10; }
        bytes memory buffer = new bytes(digits);
        while (value != 0) { digits -= 1; buffer[digits] = bytes1(uint8(48 + uint256(value % 10))); value /= 10; }
        return string(buffer);
    }
}
