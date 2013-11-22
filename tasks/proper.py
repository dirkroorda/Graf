# -*- coding: utf8 -*-
import collections
import sys

features = {
    "node": "db:otype,monads,maxmonad,minmonad ft:noun_type,gender,part_of_speech sft:verse_label,chapter,book",
    "edge": '',
}

def task(graftask):
    '''An exercise in visualizing and distant reading.

    We count proper nouns and their relative frequencies, we record the gender of the nouns.
    We produce output in various tables.

    We also produce a projection of the complete bible text to a set of symbols,
    where verbs map to ♠, male proper nouns to ♂,
    female proper nouns to ♀, and unknown gender proper nouns to ⊙.
    All other words map to a dash. Moreover, the sentence, clause and phrase
    structure is also rendered by means of boundary characters.

    Returns:
        output.txt (file): the projection of the full text as described above
    Returns:
        stats_v_raw.txt (file): a table with per verse counts for words, verbs, proper nouns per gender
    Returns:
        stats_v_compact.txt (file): a table with per verse frequencies for verbs, and proper nouns
    Returns:
        stats_c_compact.txt (file): a table with per chapter frequencies for verbs, and proper nouns
    '''
    (msg, NNi, NNr, NEi, NEr, Vi, Vr, NN, NNFV, FNi, FNr, FEi, FEr) = graftask.get_mappings()

    out = graftask.add_result("output.txt")
    stats_v_raw = graftask.add_result("stats_v_raw.txt")
    stats_v_compact = graftask.add_result("stats_v_compact.txt")
    stats_c_compact = graftask.add_result("stats_c_compact.txt")

    type_map = collections.defaultdict(lambda: None, [
        ("chapter", 'Ch'),
        ("verse", 'V'),
        ("sentence", 'S'),
        ("clause", 'C'),
        ("phrase", 'P'),
        ("word", 'w'),
    ])
    otypes = ['Ch', 'V', 'S', 'C', 'P', 'w']
    watch = collections.defaultdict(lambda: {})
    start = {}
    cur_verse_label = ['','']
#   stats_v: counts in each verse: all words, verbs, proper nouns, masc proper nouns, proper nouns, proper nouns unknown gender
    stats_v = [None, 0, 0, 0, 0, 0]
    stats_c = [None, 0, 0, 0, 0, 0]

    def print_node(ob, obdata):
        (node, minm, maxm, monads) = obdata
        if ob == "w":
            if not watch:
                out.write(u"◘".format(monads))
            else:
                outchar = u"─"
                stats_v[0] += 1
                stats_c[0] += 1
                p_o_s = FNi(node, NNi["ft.part_of_speech"])
                if p_o_s == Vi["noun"]:
                    if FNi(node, NNi["ft.noun_type"]) == Vi["proper"]:
                        stats_v[2] += 1
                        stats_c[2] += 1
                        if FNi(node, NNi["ft.gender"]) == Vi["masculine"]:
                            outchar = u"♂"
                            stats_v[3] += 1
                            stats_c[3] += 1
                        elif FNi(node, NNi["ft.gender"]) == Vi["feminine"]:
                            outchar = u"♀"
                            stats_v[4] += 1
                            stats_c[4] += 1
                        elif FNi(node, NNi["ft.gender"]) == Vi["unknown"]:
                            outchar = u"⊙"
                            stats_v[5] += 1
                            stats_c[5] += 1
                elif p_o_s == Vi["verb"]:
                    outchar = u"♠"
                    stats_v[1] += 1
                    stats_c[1] += 1
                out.write(outchar)
            if monads in watch:
                tofinish = watch[monads]
                for o in reversed(otypes):
                    if o in tofinish:
                        if o == 'C':
                            out.write(u"┤")
                        elif o == 'P':
                            if 'C' not in tofinish:
                                out.write(u"┼")
                        elif o != 'S':
                            out.write(u"{}»".format(o))
                del watch[monads]
        elif ob == "Ch":
            this_chapter_label = "{} {}".format(FNr(node, NNi["sft.book"]), FNr(node, NNi["sft.chapter"]))
            if stats_c[0] == None:
                stats_c_compact.write("\t".join(('chapter', 'word', 'verb_f', 'proper_f')) + "\n")
            else:
                n_proper = float(stats_c[0])
                stats_c_compact.write("{}\t{:.3g}\t{:.3g}\n".format(stats_c[0], 100 * stats_c[1]/n_proper, 100 * stats_c[2]/n_proper))
            for i in range(6):
                stats_c[i] = 0
            stats_c_compact.write(this_chapter_label + "\t")
        elif ob == "V":
            this_verse_label = FNr(node, NNi["sft.verse_label"]).strip(" ")
            sys.stderr.write("\r{:<11}".format(this_verse_label))
            if stats_v[0] == None:
                stats_v_raw.write("\t".join(('verse', 'word', 'verb', 'proper', 'masc', 'fem', 'unknown')) + "\n")
                stats_v_compact.write("\t".join(('verse', 'word', 'verb_f', 'proper_f')) + "\n")
            else:
                n_proper = float(stats_v[0])
                stats_v_raw.write("\t".join([str(stat) for stat in stats_v]) + "\n")
                stats_v_compact.write("{}\t{:.3g}\t{:.3g}\n".format(stats_v[0], 100 * stats_v[1]/n_proper, 100 * stats_v[2]/n_proper))
            for i in range(6):
                stats_v[i] = 0
            stats_v_raw.write(this_verse_label + "\t")
            stats_v_compact.write(this_verse_label + "\t")
            cur_verse_label[0] = this_verse_label
            cur_verse_label[1] = this_verse_label
        elif ob == "S":
            out.write("\n{:<11} ".format(cur_verse_label[1]))
            cur_verse_label[1] = ''
            watch[maxm][ob] = None
        elif ob == "C":
            out.write(u"├")
            watch[maxm][ob] = None
        elif ob == "P":
            watch[maxm][ob] = None
        else:
            out.write(u"«{}".format(ob))
            watch[maxm][ob] = None

    lastmin = None
    lastmax = None

    for i in NN():
        otype = FNr(i, NNi["db.otype"])
        if not otype:
            continue

        ob = type_map[otype]
        if ob == None:
            continue
        monads = FNr(i, NNi["db.monads"])
        minm = FNr(i, NNi["db.minmonad"])
        maxm = FNr(i, NNi["db.maxmonad"])
        if lastmin == minm and lastmax == maxm:
            start[ob] = (i, minm, maxm, monads)
        else:
            for o in otypes:
                if o in start:
                    print_node(o, start[o])
            start = {ob: (i, minm, maxm, monads)}
            lastmin = minm
            lastmax = maxm
    stats_v_raw.write("\t".join([str(stat) for stat in stats_v]) + "\n")
    n_proper = float(stats_v[0])
    stats_v_compact.write("{}\t{:.3g}\t{:.3g}\n".format(stats_v[0], stats_v[1]/n_proper, stats_v[2]/n_proper))
    n_proper = float(stats_c[0])
    stats_c_compact.write("{}\t{:.3g}\t{:.3g}\n".format(stats_c[0], stats_c[1]/n_proper, stats_c[2]/n_proper))
    for ob in otypes:
        if ob in start:
            print_node(ob, start[ob])
