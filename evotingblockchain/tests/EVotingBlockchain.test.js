const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("EVotingBlockchain", function () {
  let c, admin, a, b, v1, v2, v3, outsider;
  const H = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));
  const ZERO = ethers.ZeroHash;

  async function newElection(startOffset = 1000, dur = 5000) {
    const now = await time.latest();
    const start = now + startOffset, end = start + dur;
    await c.createElection("Pemilihan Uji", start, end, ZERO);
    const id = await c.electionCount();
    return { id, start, end };
  }
  async function ready() {
    const e = await newElection();
    await c.addCandidate(e.id, 1, "Kandidat A", H("a"));
    await c.addCandidate(e.id, 2, "Kandidat B", H("b"));
    await c.publishElection(e.id);
    await c.approveVoter(e.id, v1.address, H("id1"));
    await c.approveVoter(e.id, v2.address, H("id2"));
    return e;
  }

  beforeEach(async function () {
    [admin, a, b, v1, v2, v3, outsider] = await ethers.getSigners();
    c = await (await ethers.getContractFactory("EVotingBlockchain")).deploy();
  });

  describe("Otorisasi", function () {
    it("deployer menjadi panitia, non-panitia ditolak", async function () {
      expect(await c.isPanitia(admin.address)).to.equal(true);
      expect(await c.isPanitia(outsider.address)).to.equal(false);
      const now = await time.latest();
      await expect(c.connect(outsider).createElection("X", now + 100, now + 200, ZERO)).to.be.reverted;
      await expect(c.connect(outsider).approveVoter(1, v1.address, H("x"))).to.be.reverted;
      await expect(c.connect(outsider).buatBatchSuara(1, "B1", "x")).to.be.reverted;
    });
    it("admin dapat memberi dan mencabut role panitia", async function () {
      const role = await c.PANITIA_ROLE();
      await c.grantRole(role, a.address);
      expect(await c.isPanitia(a.address)).to.equal(true);
      await c.revokeRole(role, a.address);
      expect(await c.isPanitia(a.address)).to.equal(false);
    });
  });

  describe("Periode dan kandidat", function () {
    it("validasi waktu dan nama", async function () {
      const now = await time.latest();
      await expect(c.createElection("", now + 100, now + 200, ZERO)).to.be.revertedWithCustomError(c, "EmptyName");
      await expect(c.createElection("X", now + 200, now + 100, ZERO)).to.be.revertedWithCustomError(c, "InvalidTimeRange");
      await expect(c.createElection("X", now - 10, now + 100, ZERO)).to.be.revertedWithCustomError(c, "StartMustBeInFuture");
    });
    it("nomor urut tidak boleh duplikat dalam satu periode tetapi boleh antarperiode", async function () {
      const e1 = await newElection();
      await c.addCandidate(e1.id, 1, "A", ZERO);
      await expect(c.addCandidate(e1.id, 1, "B", ZERO)).to.be.revertedWithCustomError(c, "DuplicateNomorUrut");
      const e2 = await newElection();
      await c.addCandidate(e2.id, 1, "C", ZERO);
      expect((await c.getElection(e2.id)).activeCandidates).to.equal(1);
    });
    it("publikasi membutuhkan minimal dua kandidat aktif", async function () {
      const e = await newElection();
      await c.addCandidate(e.id, 1, "A", ZERO);
      await expect(c.publishElection(e.id)).to.be.revertedWithCustomError(c, "NeedTwoCandidates");
    });
    it("kandidat dapat diedit dan dihapus sebelum mulai, nomor urut bebas lagi", async function () {
      const e = await newElection();
      await c.addCandidate(e.id, 1, "A", ZERO);
      await c.addCandidate(e.id, 2, "B", ZERO);
      await c.addCandidate(e.id, 3, "C", ZERO);
      await c.updateCandidate(e.id, 1, 4, "A2", H("a2"));
      expect((await c.getCandidate(e.id, 1)).name).to.equal("A2");
      await c.removeCandidate(e.id, 3);
      await c.addCandidate(e.id, 3, "C-baru", ZERO);
      await expect(c.updateCandidate(e.id, 2, 4, "B", ZERO)).to.be.revertedWithCustomError(c, "DuplicateNomorUrut");
    });
    it("kandidat dan periode terkunci setelah waktu mulai", async function () {
      const e = await ready();
      await time.increaseTo(e.start + 1);
      await expect(c.addCandidate(e.id, 3, "C", ZERO)).to.be.revertedWithCustomError(c, "ElectionAlreadyStarted");
      await expect(c.updateCandidate(e.id, 1, 1, "X", ZERO)).to.be.revertedWithCustomError(c, "ElectionAlreadyStarted");
      await expect(c.removeCandidate(e.id, 1)).to.be.revertedWithCustomError(c, "ElectionAlreadyStarted");
      await expect(c.updateElection(e.id, "Baru", e.start + 10, e.end, ZERO)).to.be.revertedWithCustomError(c, "ElectionAlreadyStarted");
    });
    it("periode yang dipublikasikan tidak boleh turun di bawah dua kandidat", async function () {
      const e = await ready();
      await expect(c.removeCandidate(e.id, 1)).to.be.revertedWithCustomError(c, "NeedTwoCandidates");
    });
  });

  describe("Registrasi dan voting", function () {
    it("pemilih terverifikasi dapat memilih tepat satu kali", async function () {
      const e = await ready();
      await time.increaseTo(e.start + 1);
      await expect(c.connect(v1).vote(e.id, 1)).to.emit(c, "VoteCast").withArgs(e.id, v1.address);
      expect(await c.hasVoted(e.id, v1.address)).to.equal(true);
      await expect(c.connect(v1).vote(e.id, 2)).to.be.revertedWithCustomError(c, "AlreadyVoted");
      const r = await c.getResults(e.id);
      expect(r.votes.map(Number)).to.deep.equal([1, 0]);
      expect((await c.getElection(e.id)).totalVotes).to.equal(1);
    });
    it("pemilih tidak terdaftar ditolak", async function () {
      const e = await ready();
      await time.increaseTo(e.start + 1);
      await expect(c.connect(v3).vote(e.id, 1)).to.be.revertedWithCustomError(c, "VoterNotEligible");
    });
    it("voting ditolak sebelum mulai, setelah selesai, dan pada periode dibatalkan", async function () {
      const e = await ready();
      await expect(c.connect(v1).vote(e.id, 1)).to.be.revertedWithCustomError(c, "VotingNotOpen");
      await time.increaseTo(e.end + 1);
      await expect(c.connect(v1).vote(e.id, 1)).to.be.revertedWithCustomError(c, "VotingNotOpen");
      const e2 = await ready2();
      await c.cancelElection(e2.id);
      await time.increaseTo(e2.start + 1);
      await expect(c.connect(v1).vote(e2.id, 1)).to.be.revertedWithCustomError(c, "VotingNotOpen");
    });
    async function ready2() {
      const e = await newElection(10, 5000);
      await c.addCandidate(e.id, 1, "A", ZERO);
      await c.addCandidate(e.id, 2, "B", ZERO);
      await c.publishElection(e.id);
      await c.approveVoter(e.id, v1.address, H("idx"));
      return e;
    }
    it("kandidat tidak valid ditolak", async function () {
      const e = await ready();
      await time.increaseTo(e.start + 1);
      await expect(c.connect(v1).vote(e.id, 9)).to.be.revertedWithCustomError(c, "CandidateNotFound");
    });
    it("satu identitas tidak dapat dipakai dua wallet dalam periode yang sama", async function () {
      const e = await ready();
      await expect(c.approveVoter(e.id, v3.address, H("id1"))).to.be.revertedWithCustomError(c, "CredentialAlreadyUsed");
      await expect(c.approveVoter(e.id, v1.address, H("lain"))).to.be.revertedWithCustomError(c, "AlreadyApproved");
    });
    it("hak memilih terpisah antarperiode", async function () {
      const e1 = await ready();
      const e2 = await newElection();
      expect(await c.isEligible(e2.id, v1.address)).to.equal(false);
      expect(await c.isEligible(e1.id, v1.address)).to.equal(true);
    });
  });

  describe("Finalisasi dan audit checkpoint", function () {
    async function voted() {
      const e = await ready();
      await time.increaseTo(e.start + 1);
      await c.connect(v1).vote(e.id, 1);
      await c.connect(v2).vote(e.id, 1);
      return e;
    }
    it("finalisasi hanya setelah periode berakhir dan membuat checkpoint", async function () {
      const e = await voted();
      await expect(c.finalizeElection(e.id)).to.be.revertedWithCustomError(c, "ElectionNotEnded");
      await time.increaseTo(e.end + 1);
      await expect(c.finalizeElection(e.id)).to.emit(c, "ElectionFinalized");
      expect((await c.getElection(e.id)).state).to.equal(3);
      expect(await c.getBlockchainLength()).to.equal(1);
      await expect(c.finalizeElection(e.id)).to.be.revertedWithCustomError(c, "InvalidState");
      await expect(c.cancelElection(e.id)).to.be.revertedWithCustomError(c, "InvalidState");
    });
    it("rantai checkpoint, verifikasi, dan transisi status", async function () {
      const e = await voted();
      await c.buatBatchSuara(e.id, "BATCH-1", "Snapshot 1");
      await c.buatBatchSuara(e.id, "BATCH-2", "Snapshot 2");
      await expect(c.buatBatchSuara(e.id, "BATCH-1", "dup")).to.be.revertedWithCustomError(c, "BatchIdExists");
      await expect(c.buatBatchSuara(e.id, "FINAL-1", "x")).to.be.revertedWithCustomError(c, "BatchIdExists");
      expect(await c.getBlockchainLength()).to.equal(2);
      const b2 = await c.getBlock(2);
      const b1 = await c.getBlock(1);
      expect(b2.previousHash).to.equal(b1.blockHash);
      expect(b1.previousHash).to.equal(ZERO);
      expect((await c.cekIntegritasRantai()).valid).to.equal(true);
      await expect(c.rekapitulasiBertingkat(1)).to.be.revertedWithCustomError(c, "InvalidTransition");
      await c.verifikasiLokal(1);
      await c.rekapitulasiBertingkat(1);
      await expect(c.penghitunganAkhir(1)).to.be.revertedWithCustomError(c, "ElectionNotFinalized");
      await time.increaseTo(e.end + 1);
      await c.finalizeElection(e.id);
      await c.penghitunganAkhir(1);
      expect((await c.getBlock(1)).status).to.equal(4);
      const h = await c.getHistory("BATCH-1");
      expect(h.map((x) => x.eventType)).to.deep.equal(["VOTE_BATCH_CREATED", "VERIFIED_LOCAL", "IN_RECAP", "FINISHED"]);
      expect(await c.getBlockIndexByBatchId("BATCH-2")).to.equal(2);
    });
    it("verifikasi hanya untuk panitia", async function () {
      const e = await voted();
      await c.buatBatchSuara(e.id, "BATCH-1", "x");
      await expect(c.connect(outsider).verifikasiLokal(1)).to.be.reverted;
      await expect(c.connect(outsider).rekapitulasiBertingkat(1)).to.be.reverted;
      await expect(c.connect(outsider).penghitunganAkhir(1)).to.be.reverted;
    });
  });
});
