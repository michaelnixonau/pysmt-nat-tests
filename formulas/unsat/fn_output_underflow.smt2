; Output of a fn. returning a Nat should be constrained to >= 0
; We checke that f(a) + 1 = 0 is UNSAT (as f(a) would need to eval. to -1)
(declare-const x Nat)
(declare-fun f (Nat) Nat)
(assert (= (+ (f a) 1) 0))