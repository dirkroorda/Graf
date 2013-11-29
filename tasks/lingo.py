# -*- coding: utf8 -*-

import collections
import sys

load = {
    "xmlids": {
        "node": False,
        "edge": False,
    },
    "features": {
        "node": "db:otype,monads,maxmonad,minmonad ft:gender,part_of_speech sft:verse_label",
        "edge": '',
    }
}

def task(graftask):
    (msg, Vi, Vr, NN, NNFV, FN, FE, XNi, XNr, XEi, XEr) = graftask.get_mappings()

    out = graftask.add_result("output.txt")

    type_map = collections.defaultdict(lambda: None, [
        ("verse", 'V'),
        ("sentence", 'S'),
        ("sentence_atom", 's'),
        ("clause", 'C'),
        ("clause_atom", 'c'),
        ("phrase", 'P'),
        ("phrase_atom", 'p'),
        ("subphrase", 'q'),
        ("word", 'w'),
    ])
    otypes = ['V', 'S', 's', 'C', 'c', 'P', 'p', 'q', 'w']

    watch = collections.defaultdict(lambda: {})
    start = {}
    cur_verse_label = ['','']

    def print_node(ob, obdata):
        (node, minm, maxm, monads) = obdata
        if ob == "w":
            if not watch:
                out.write("◘".format(monads))
            else:
                outchar = "."
                if FN(node, "ft.part_of_speech") == Vi["noun"]:
                    if FN(node, "ft.gender") == Vi["masculine"]:
                        outchar = "♂"
                    elif FN(node, "ft.gender") == Vi["feminine"]:
                        outchar = "♀"
                    elif FN(node, "ft.gender") == Vi["unknown"]:
                        outchar = "?"
                if FN(node, "ft.part_of_speech") == Vi["verb"]:
                    outchar = "♠"
                out.write(outchar)
            if monads in watch:
                tofinish = watch[monads]
                for o in reversed(otypes):
                    if o in tofinish:
                        out.write("{})".format(o))
                del watch[monads]
        elif ob == "V":
            this_verse_label = Vr[FN(node, "sft.verse_label")]
            cur_verse_label[0] = this_verse_label
            cur_verse_label[1] = this_verse_label
        elif ob == "S":
            out.write("\n{:<11}{{{:>6}-{:>6}}} ".format(cur_verse_label[1], minm, maxm))
            cur_verse_label[1] = ''
            sys.stderr.write("\r{:>6}-{:>6}".format(minm, maxm))
            out.write("({}".format(ob))
            watch[maxm][ob] = None
        else:
            out.write("({}".format(ob))
            watch[maxm][ob] = None

    lastmin = None
    lastmax = None

    for i in NN():
        otype = Vr[FN(i, "db.otype")]
        if not otype:
            continue

        ob = type_map[otype]
        if ob == None:
            continue
        monads = Vr[FN(i, "db.monads")]
        minm = Vr[FN(i, "db.minmonad")]
        maxm = Vr[FN(i, "db.maxmonad")]
        if lastmin == minm and lastmax == maxm:
            start[ob] = (i, minm, maxm, monads)
        else:
            for o in otypes:
                if o in start:
                    print_node(o, start[o])
            start = {ob: (i, minm, maxm, monads)}
            lastmin = minm
            lastmax = maxm
    for ob in otypes:
        if ob in start:
            print_node(ob, start[ob])

