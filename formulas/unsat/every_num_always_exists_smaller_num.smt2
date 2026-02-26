; Assert: for every number, there is a smaller number
; This is unsatisfiable for Nats
(assert
    (forall ((x Nat))
        (exists ((y Nat))
            (< y x)
        )
    )
)