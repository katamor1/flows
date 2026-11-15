	.def	@feat.00;
	.scl	3;
	.type	0;
	.endef
	.globl	@feat.00
@feat.00 = 0
	.file	"AlarmQualification.c"
	.def	AlarmQualification_Update;
	.scl	2;
	.type	32;
	.endef
	.text
	.globl	AlarmQualification_Update       # -- Begin function AlarmQualification_Update
	.p2align	4
AlarmQualification_Update:              # @AlarmQualification_Update
# %bb.0:
	movl	$-1, %eax
	testq	%rcx, %rcx
	je	.LBB0_6
# %bb.1:
	testq	%r9, %r9
	je	.LBB0_6
# %bb.2:
	movl	$-2, %eax
	cmpl	$1, %r8d
	ja	.LBB0_6
# %bb.3:
	sete	%r10b
	cmpl	$2, %edx
	setae	%r11b
	testb	%r10b, %r11b
	jne	.LBB0_6
# %bb.4:
	movl	(%rcx), %r10d
	movl	$-3, %eax
	cmpl	$10, %r10d
	ja	.LBB0_6
# %bb.5:
	leal	1(%r10), %eax
	cmpl	$10, %r10d
	cmovel	%r10d, %eax
	setne	%r10b
	testl	%r8d, %r8d
	cmovel	%r8d, %eax
	testl	%edx, %edx
	cmovel	%edx, %eax
	xorl	%edx, %edx
	cmpl	$10, %eax
	sete	%dl
	movl	%eax, (%rcx)
	movl	%edx, (%r9)
	movl	%edx, %ecx
	andb	%r10b, %cl
	movzbl	%cl, %ecx
	movl	%ecx, 4(%r9)
	movl	%eax, 8(%r9)
	xorl	%eax, %eax
.LBB0_6:
	retq
                                        # -- End function
	.section	.debug$S,"dr"
	.p2align	2, 0x0
	.long	4                               # Debug section magic
	.long	241
	.long	.Ltmp1-.Ltmp0                   # Subsection size
.Ltmp0:
	.short	.Ltmp3-.Ltmp2                   # Record length
.Ltmp2:
	.short	4353                            # Record kind: S_OBJNAME
	.long	0                               # Signature
	.byte	0                               # Object name
	.p2align	2, 0x0
.Ltmp3:
	.short	.Ltmp5-.Ltmp4                   # Record length
.Ltmp4:
	.short	4412                            # Record kind: S_COMPILE3
	.long	0                               # Flags and language
	.short	208                             # CPUType
	.short	22                              # Frontend version
	.short	1
	.short	3
	.short	0
	.short	22013                           # Backend version
	.short	0
	.short	0
	.short	0
	.asciz	"clang version 22.1.3 (https://github.com/llvm/llvm-project e9846648fd6183ee6d8cbdb4502213fcf902a211)" # Null-terminated compiler version string
	.p2align	2, 0x0
.Ltmp5:
.Ltmp1:
	.p2align	2, 0x0
	.addrsig
