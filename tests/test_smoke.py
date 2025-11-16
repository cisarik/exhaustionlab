def test_import():
    import exhaustionlab

    assert hasattr(exhaustionlab, "__all__")
